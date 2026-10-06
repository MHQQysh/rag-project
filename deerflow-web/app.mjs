import {
  LIMITS,
  chunkDocument,
  retrieve,
  buildMessages,
  exportConversation,
} from "./core.mjs";
import { streamChat } from "./model.mjs";
const $ = (id) => document.getElementById(id);
let docs = [],
  turns = [],
  controller = null,
  busy = false;
const setStatus = (text, error = false) => {
  $("status").textContent = text;
  $("status").classList.toggle("error", error);
};
function lock(value) {
  busy = value;
  for (const id of [
    "send",
    "preview",
    "files",
    "sample",
    "clear-docs",
    "new-chat",
    "model",
    "api-key",
    "question",
    "export",
  ])
    $(id).disabled = value;
  document
    .querySelectorAll("[data-question]")
    .forEach((b) => (b.disabled = value));
  $("stop").hidden = !value;
}
function refreshDocs() {
  $("file-list").replaceChildren();
  for (const d of docs) {
    const li = document.createElement("li");
    li.textContent = `${d.name} · ${d.chunks.length} 块`;
    $("file-list").append(li);
  }
  $("doc-count").textContent = `${docs.length} 份`;
}
function showSources(hits) {
  $("sources").hidden = false;
  $("source-count").textContent = `${hits.length} 个片段`;
  $("source-list").replaceChildren();
  if (!hits.length) {
    const p = document.createElement("p");
    p.className = "note";
    p.textContent = docs.length
      ? "没有找到包含查询关键词的片段。试试更具体的词语，或换一种表述。"
      : "还没有资料。可在左侧添加文件或载入示例。";
    $("source-list").append(p);
  }
  for (const hit of hits) {
    const detail = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = `[${hit.id}] ${hit.name} · 第 ${hit.index} 块`;
    const pre = document.createElement("pre");
    pre.textContent = hit.text;
    detail.append(summary, pre);
    $("source-list").append(detail);
  }
}
function findSources() {
  return retrieve(
    $("question").value,
    docs.flatMap((d) => d.chunks),
  );
}
function message(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const h = document.createElement("h2");
  h.textContent = role === "user" ? "YOU / 你的问题" : "DEEPSEEK / 回答";
  const body = document.createElement("div");
  body.className = "text";
  body.textContent = text;
  article.append(h, body);
  $("messages").append(article);
  return { article, body };
}
function scrollLatest() {
  const content = document.querySelector(".content");
  if (content.scrollHeight - content.scrollTop - content.clientHeight < 300)
    content.scrollTop = content.scrollHeight;
}
$("files").addEventListener("change", async () => {
  const incoming = [...$("files").files];
  if (!incoming.length) return;
  lock(true);
  try {
    if (docs.length + incoming.length > LIMITS.files)
      throw Error("最多同时添加 8 份资料");
    if (
      docs.reduce((n, d) => n + d.size, 0) +
        incoming.reduce((n, f) => n + f.size, 0) >
      LIMITS.totalBytes
    )
      throw Error("资料总大小不能超过 4 MB");
    const additions = [];
    for (const file of incoming) {
      if (!/\.(txt|md|markdown)$/i.test(file.name))
        throw Error("目前只支持 UTF-8 TXT / Markdown 文件，不支持 PDF 或 Word");
      if (file.size > LIMITS.fileBytes) throw Error("单份资料不能超过 1 MB");
      const text = await file.text();
      if (text.includes("\0") || text.includes("\uFFFD"))
        throw Error("资料不是有效 UTF-8 文本，请转换编码后重试");
      const chunks = chunkDocument(file.name, text);
      if (!chunks.length) throw Error("资料内容为空");
      additions.push({ name: file.name, size: file.size, chunks });
    }
    docs.push(...additions);
    refreshDocs();
    $("sources").hidden = true;
    setStatus("资料已在浏览器中分块。输入问题后可先点击“只看检索”。");
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    $("files").value = "";
    lock(false);
  }
});
$("sample").addEventListener("click", () => {
  if (docs.some((d) => d.name === "示例-RAG与Agent.md")) {
    setStatus("示例资料已经载入");
    return;
  }
  const text = `# RAG 与 Agent 学习笔记\n\n## RAG 的流程\nRAG 是检索增强生成：先把文档切成片段并建立索引，再根据问题检索相关片段，最后把问题和片段交给模型生成带出处的回答。检索未命中时应明确缺少依据。\n\n## 分块与检索\n固定长度分块简单，但可能切断语义；段落分块保持自然边界，但长度不均匀；层级分块保留标题关系，但需要更复杂的解析。相邻片段保留少量重叠可降低边界信息丢失。关键词检索适合精确术语，向量检索有助于语义相似匹配，两者不能混为一谈。\n\n## Agent、Tool、Skill\nAgent 根据当前上下文选择下一步。Tool 是程序提供的可执行接口。Skill 是可复用的方法说明与资源，指导 Agent 如何做事，但不凭空赋予权限。\n\n## 完整 DeerFlow 与浏览器版\n完整 DeerFlow 通过 Python 后端组织模型、工具、子 Agent、运行状态和记忆。这个 DeerFlow Web 是独立浏览器轻量版，只实现聊天、文档关键词检索与导出，不运行 LangGraph、代码沙箱或联网搜索。\n\n## 上下文管理\n上下文不是无限的。可以限制工具输出、选取相关片段、保留最近对话或生成摘要。本网页版限制最近对话和检索片段长度，不实现长期记忆或模型摘要。`;
  if (
    docs.length >= LIMITS.files ||
    docs.reduce((n, d) => n + d.size, 0) +
      new TextEncoder().encode(text).length >
      LIMITS.totalBytes
  ) {
    setStatus("资料数量或总大小已达到上限", true);
    return;
  }
  docs.push({
    name: "示例-RAG与Agent.md",
    size: new TextEncoder().encode(text).length,
    chunks: chunkDocument("示例-RAG与Agent.md", text),
  });
  refreshDocs();
  $("sources").hidden = true;
  setStatus("示例已载入。试着问“RAG 分块和检索有什么关系？”");
});
$("clear-docs").addEventListener("click", () => {
  docs = [];
  refreshDocs();
  $("sources").hidden = true;
  setStatus("资料已清空；历史对话仍保留，可点“新对话”重置。");
});
$("clear-key").addEventListener("click", () => {
  controller?.abort();
  $("api-key").value = "";
  setStatus("Key 已清除；若有请求在运行，已请求停止。");
});
$("new-chat").addEventListener("click", () => {
  turns = [];
  $("messages").replaceChildren();
  $("sources").hidden = true;
  $("welcome").hidden = false;
  $("question").value = "";
  setStatus("已开始新对话。模型设置和资料继续保留。");
});
$("preview").addEventListener("click", () => {
  if (!$("question").value.trim()) {
    setStatus("先输入一个问题再检索", true);
    return;
  }
  const hits = findSources();
  showSources(hits);
  $("sources").scrollIntoView({ behavior: "smooth", block: "nearest" });
  setStatus(`检索完成：${hits.length} 个片段。尚未调用模型，没有 API 费用。`);
});
document.querySelectorAll("[data-question]").forEach((b) =>
  b.addEventListener("click", () => {
    $("question").value = b.dataset.question;
    $("question").focus();
  }),
);
$("question").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    if (!busy) $("chat-form").requestSubmit();
  }
});
$("stop").addEventListener("click", () => controller?.abort());
$("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (busy) return;
  const query = $("question").value.trim();
  if (!query) {
    setStatus("请先输入问题", true);
    return;
  }
  if (!$("api-key").value.trim()) {
    setStatus(
      "请在左侧输入你自己的 DeepSeek API Key；只看检索不需要 Key。",
      true,
    );
    $("api-key").focus();
    return;
  }
  const hits = findSources();
  showSources(hits);
  const history = turns
    .filter((t) => t.complete)
    .flatMap((t) => [
      { role: "user", content: t.query },
      { role: "assistant", content: t.answer },
    ]);
  const messages = buildMessages(history, query, hits, docs.length > 0);
  const turn = {
    query,
    answer: "",
    hits,
    model: $("model").value,
    complete: false,
    outcome: "生成中",
  };
  turns.push(turn);
  $("welcome").hidden = true;
  message("user", query);
  const view = message("assistant", "正在等待模型…");
  lock(true);
  controller = new AbortController();
  setStatus("正在连接 DeepSeek，收到内容后会逐步显示…");
  try {
    await streamChat({
      key: $("api-key").value,
      model: turn.model,
      messages,
      signal: controller.signal,
      onDelta: (part) => {
        turn.answer += part;
        view.body.textContent = turn.answer;
        setStatus("正在生成 · 可随时停止");
        scrollLatest();
      },
    });
    turn.complete = true;
    turn.outcome = "已完成";
    setStatus(`回答完成 · ${hits.length} 个资料片段作为依据。可导出对话。`);
    $("question").value = "";
  } catch (error) {
    turn.outcome = error.message;
    const p = document.createElement("p");
    p.className = "outcome";
    p.textContent = error.message;
    view.article.append(p);
    if (!turn.answer) view.body.textContent = "没有生成回答。";
    setStatus(error.message, true);
  } finally {
    controller = null;
    lock(false);
    $("question").focus();
  }
});
$("export").addEventListener("click", () => {
  if (!turns.length) {
    setStatus("还没有可导出的对话", true);
    return;
  }
  const output = exportConversation(turns);
  const url = URL.createObjectURL(
    new Blob([output], { type: "text/markdown;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "deerflow-conversation.md";
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  setStatus("已发起 Markdown 下载，包含回答与本轮原文依据。");
});
