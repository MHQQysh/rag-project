const state = { conversationId: null, sending: false, sources: [] };
const $ = (id) => document.getElementById(id);

function escapeHtml(value = "") {
  return value.replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function renderMarkdown(text = "") {
  let safe = escapeHtml(text);
  safe = safe.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code.trim()}</code></pre>`);
  safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
  safe = safe.replace(/^### (.+)$/gm, "<h3>$1</h3>").replace(/^## (.+)$/gm, "<h2>$1</h2>");
  safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  safe = safe.split(/\n{2,}/).map((part) => part.startsWith("<pre") ? part : `<p>${part.replace(/\n/g, "<br>")}</p>`).join("");
  return safe;
}

function renderAnswer(text) {
  const end = text.indexOf("</think>");
  if (end >= 0) {
    const thought = text.startsWith("<think>") ? text.slice(7, end) : text.slice(0, end);
    const answer = text.slice(end + 8);
    return `<details class="thinking"><summary>查看推理过程</summary><div>${escapeHtml(thought)}</div></details>${renderMarkdown(answer)}`;
  }
  if (text.startsWith("<think>")) {
    return `<details class="thinking" open><summary>正在推理…</summary><div>${escapeHtml(text.slice(7))}</div></details>`;
  }
  return renderMarkdown(text);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try { message = (await response.json()).detail || message; } catch (_) {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function toast(message) {
  const element = $("toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(element.timer);
  element.timer = setTimeout(() => element.classList.remove("show"), 2600);
}

function sourceHtml(sources = []) {
  if (!sources.length) return "";
  return `<div class="sources">${sources.map((source, index) => `
    <details class="source-card">
      <summary><span class="source-index">${index + 1}</span><span class="source-title">${escapeHtml(source.document_name)} · ${escapeHtml(source.locator || "未标注")}</span><span class="source-score">${Math.round(source.score * 100)}%</span></summary>
      <div class="score-breakdown"><span>混合 ${Math.round(source.score * 100)}%</span><span>语义 ${Math.round((source.dense_score || 0) * 100)}%</span><span>词法 ${Math.round((source.lexical_score || 0) * 100)}%</span><span>实体 ${Math.round((source.entity_score || 0) * 100)}%</span></div>
      <p>${escapeHtml(source.content)}</p>
    </details>`).join("")}</div>`;
}

function chipList(values = [], empty = "无") {
  if (!values.length) return `<span class="analysis-empty">${empty}</span>`;
  return values.map((value) => `<span class="analysis-chip">${escapeHtml(String(value))}</span>`).join("");
}

function analysisHtml(analysis = {}) {
  if (!analysis.tokens) return "";
  const entities = (analysis.entities || []).map((item) => `${item.text} · ${item.type}`);
  const keywords = (analysis.keywords || []).map((item) => item.text);
  const normalizations = (analysis.normalizations || []).map((item) => `${item.original} → ${item.normalized}`);
  return `<details class="query-analysis" open>
    <summary>检索理解 <span>语义 + BM25 + 实体加权</span></summary>
    <div class="analysis-grid">
      <div><b>① 分词</b><section>${chipList(analysis.tokens)}</section></div>
      <div><b>② 去停用词</b><section>${chipList(analysis.filtered_tokens)}</section><small>移除：${escapeHtml((analysis.removed_stopwords || []).join("、") || "无")}</small></div>
      <div><b>③ 词形归一</b><section>${chipList(normalizations, "中文无需词干化；未发现英文词形变化")}</section></div>
      <div><b>④ 实体识别</b><section>${chipList(entities)}</section></div>
      <div><b>⑤ 关键词</b><section>${chipList(keywords)}</section></div>
      <div><b>⑥ 语义理解</b><small>${escapeHtml(analysis.semantic_strategy || "完整问题由 BGE-M3 编码")}</small></div>
    </div>
  </details>`;
}

function addMessage(role, content, sources = [], streaming = false, analysis = {}) {
  $("emptyState").classList.add("hidden");
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;
  wrapper.innerHTML = `<div class="avatar">${role === "user" ? "YOU" : "DS"}</div><div class="message-content ${streaming ? "typing" : ""}"></div>`;
  const body = wrapper.querySelector(".message-content");
  body.innerHTML = role === "assistant" ? analysisHtml(analysis) + renderAnswer(content) + sourceHtml(sources) : renderMarkdown(content);
  wrapper.dataset.content = content;
  $("messages").appendChild(wrapper);
  scrollBottom();
  return wrapper;
}

function updateAssistant(element, content, sources, streaming, analysis = {}) {
  element.dataset.content = content;
  const body = element.querySelector(".message-content");
  body.classList.toggle("typing", streaming);
  body.innerHTML = analysisHtml(analysis) + renderAnswer(content) + sourceHtml(sources);
  scrollBottom();
}

function scrollBottom() {
  const panel = $("chatPanel");
  panel.scrollTop = panel.scrollHeight;
}

async function loadStats() {
  const stats = await api("/api/stats");
  $("docCount").textContent = stats.documents;
  $("chunkCount").textContent = stats.chunks;
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    const ready = health.status === "ok";
    $("statusDot").className = `status-dot ${ready ? "ready" : "error"}`;
    $("statusText").textContent = ready ? "全部服务正常" : "模型正在启动";
    $("modelText").textContent = health.llm.model;
  } catch (_) {
    $("statusDot").className = "status-dot error";
    $("statusText").textContent = "服务连接异常";
  }
}

async function loadConfig() {
  const config = await api("/api/config");
  $("uploadHint").textContent = `${config.supported_extensions.join(" / ")} · 最大 ${config.max_upload_mb}MB`;
  $("composerHint").textContent = `${config.model} · BGE-M3`;
}

async function loadConversations() {
  const conversations = await api("/api/conversations");
  const list = $("conversationList");
  list.innerHTML = conversations.length ? "" : '<div class="document-empty">还没有对话</div>';
  conversations.forEach((conversation) => {
    const button = document.createElement("button");
    button.className = `conversation-item ${conversation.id === state.conversationId ? "active" : ""}`;
    button.innerHTML = `<span class="bubble">◌</span><span>${escapeHtml(conversation.title)}</span><span class="conversation-delete">×</span>`;
    button.onclick = (event) => {
      if (event.target.classList.contains("conversation-delete")) return deleteConversation(conversation.id);
      openConversation(conversation.id, conversation.title);
    };
    list.appendChild(button);
  });
}

async function openConversation(id, title) {
  state.conversationId = id;
  $("pageTitle").textContent = title;
  const messages = await api(`/api/conversations/${id}/messages`);
  $("messages").innerHTML = "";
  $("emptyState").classList.toggle("hidden", messages.length > 0);
  messages.forEach((message) => addMessage(message.role, message.content, message.sources, false, message.analysis));
  await loadConversations();
}

async function deleteConversation(id) {
  if (!confirm("删除这个会话及其全部消息？")) return;
  await api(`/api/conversations/${id}`, { method: "DELETE" });
  if (state.conversationId === id) newChat();
  await loadConversations();
}

function newChat() {
  state.conversationId = null;
  $("pageTitle").textContent = "知识库问答";
  $("messages").innerHTML = "";
  $("emptyState").classList.remove("hidden");
  loadConversations();
  $("queryInput").focus();
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

async function loadDocuments() {
  const documents = await api("/api/documents");
  $("documentTotal").textContent = documents.length;
  const list = $("documentList");
  list.innerHTML = documents.length ? "" : '<div class="document-empty">还没有资料，上传一份开始吧</div>';
  documents.forEach((doc) => {
    const item = window.document.createElement("div");
    item.className = "document-item";
    item.innerHTML = `<div class="file-icon">${escapeHtml(doc.extension.slice(1).toUpperCase())}</div><div class="document-info"><strong title="${escapeHtml(doc.name)}">${escapeHtml(doc.name)}</strong><span>${doc.status === "ready" ? `${doc.chunk_count} 个切片 · ${formatSize(doc.size_bytes)}` : escapeHtml(doc.error || doc.status)}</span></div><button class="document-remove" title="删除">×</button>`;
    item.querySelector("button").onclick = () => deleteDocument(doc.id, doc.name);
    list.appendChild(item);
  });
}

async function deleteDocument(id, name) {
  if (!confirm(`删除“${name}”及其全部向量？`)) return;
  await api(`/api/documents/${id}`, { method: "DELETE" });
  toast("文档已删除");
  await Promise.all([loadDocuments(), loadStats()]);
}

async function uploadFiles(files) {
  if (!files.length) return;
  const status = $("uploadStatus");
  status.classList.remove("hidden");
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    status.textContent = `正在解析并索引 ${index + 1}/${files.length}：${file.name}`;
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api("/api/documents", { method: "POST", body: form });
      toast(result.duplicate ? `${file.name} 已经存在` : `${file.name} 索引完成`);
    } catch (error) {
      toast(`${file.name}：${error.message}`);
    }
  }
  status.classList.add("hidden");
  $("fileInput").value = "";
  await Promise.all([loadDocuments(), loadStats()]);
}

function parseSSE(buffer, onEvent) {
  const blocks = buffer.split("\n\n");
  const remainder = blocks.pop();
  blocks.forEach((block) => {
    let event = "message";
    const data = [];
    block.split("\n").forEach((line) => {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("data:")) data.push(line.slice(5).trim());
    });
    if (data.length) onEvent(event, JSON.parse(data.join("\n")));
  });
  return remainder;
}

async function sendQuery(query) {
  if (state.sending || !query.trim()) return;
  state.sending = true;
  $("sendButton").disabled = true;
  addMessage("user", query.trim());
  const assistant = addMessage("assistant", "", [], true);
  let content = "";
  let sources = [];
  let analysis = {};
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query.trim(), conversation_id: state.conversationId, top_k: Number($("topK").value) }),
    });
    if (!response.ok) throw new Error((await response.json()).detail || "问答请求失败");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      buffer = parseSSE(buffer, (event, data) => {
        if (event === "meta") { state.conversationId = data.conversation_id; sources = data.sources || []; analysis = data.analysis || {}; updateAssistant(assistant, content, sources, true, analysis); }
        if (event === "token") { content += data.content; updateAssistant(assistant, content, sources, true, analysis); }
        if (event === "error") throw new Error(data.message);
      });
      if (done) break;
    }
    updateAssistant(assistant, content || "模型没有返回内容。", sources, false, analysis);
    await Promise.all([loadConversations(), loadStats()]);
  } catch (error) {
    updateAssistant(assistant, `请求失败：${error.message}`, sources, false, analysis);
  } finally {
    state.sending = false;
    $("sendButton").disabled = false;
    $("queryInput").focus();
  }
}

$("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = $("queryInput");
  const query = input.value;
  input.value = "";
  input.style.height = "auto";
  sendQuery(query);
});
$("queryInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("composer").requestSubmit(); }
});
$("queryInput").addEventListener("input", (event) => {
  event.target.style.height = "auto";
  event.target.style.height = `${Math.min(event.target.scrollHeight, 150)}px`;
});
$("newChat").onclick = newChat;
$("refreshDocs").onclick = () => Promise.all([loadDocuments(), loadStats()]);
$("fileInput").onchange = (event) => uploadFiles([...event.target.files]);
$("dropZone").addEventListener("dragover", (event) => { event.preventDefault(); event.currentTarget.classList.add("dragging"); });
$("dropZone").addEventListener("dragleave", (event) => event.currentTarget.classList.remove("dragging"));
$("dropZone").addEventListener("drop", (event) => { event.preventDefault(); event.currentTarget.classList.remove("dragging"); uploadFiles([...event.dataTransfer.files]); });
document.querySelectorAll(".suggestions button").forEach((button) => button.onclick = () => { $("queryInput").value = button.textContent; $("composer").requestSubmit(); });

Promise.all([loadHealth(), loadConfig(), loadStats(), loadDocuments(), loadConversations()]).catch((error) => toast(error.message));
setInterval(loadHealth, 15000);
