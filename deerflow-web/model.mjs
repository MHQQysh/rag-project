const ENDPOINT = "https://api.deepseek.com/chat/completions";
export async function streamChat({
  key,
  model = "deepseek-flash",
  messages,
  signal,
  onDelta = () => {},
  fetchImpl = fetch,
  timeoutMs = 120000,
}) {
  if (!key?.trim()) throw Error("请先输入自己的 DeepSeek API Key");
  if (!["deepseek-flash", "deepseek-v4-pro"].includes(model))
    throw Error("不支持的模型");
  const controller = new AbortController();
  let timedOut = false,
    reader;
  const stop = () => controller.abort();
  signal?.addEventListener("abort", stop, { once: true });
  if (signal?.aborted) stop();
  const timer = setTimeout(() => {
    timedOut = true;
    stop();
  }, timeoutMs);
  try {
    const response = await fetchImpl(ENDPOINT, {
      method: "POST",
      redirect: "error",
      credentials: "omit",
      referrerPolicy: "no-referrer",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${key.trim()}`,
      },
      body: JSON.stringify({
        model,
        messages,
        stream: true,
        max_tokens: 4096,
        thinking: { type: "disabled" },
      }),
      signal: controller.signal,
    });
    if (!response.ok)
      throw Error(
        {
          400: "请求参数或上下文不被模型支持",
          401: "API Key 无效或已失效",
          402: "DeepSeek 账户余额不足",
          403: "接口访问被拒绝",
          429: "请求过于频繁，请稍后重试",
        }[response.status] || `DeepSeek 服务错误（HTTP ${response.status}）`,
      );
    if (!response.body) throw Error("浏览器没有收到响应流");
    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "",
      eventLines = [],
      done = false,
      total = 0,
      finishReason = "";
    function dispatch() {
      if (!eventLines.length) return;
      const data = eventLines.join("\n");
      eventLines = [];
      if (data.trim() === "[DONE]") {
        done = true;
        return;
      }
      let parsed;
      try {
        parsed = JSON.parse(data);
      } catch {
        throw Error("响应流格式错误");
      }
      if (parsed.error) throw Error("模型服务返回流式错误，请重试");
      const choice = parsed.choices?.[0];
      if (choice?.finish_reason) finishReason = choice.finish_reason;
      const part = choice?.delta?.content;
      if (typeof part === "string" && part) {
        total += part.length;
        if (total > 100000) throw Error("响应超过长度限制");
        onDelta(part);
      }
    }
    function line(l) {
      if (l.endsWith("\r")) l = l.slice(0, -1);
      if (l === "") dispatch();
      else if (l.startsWith("data:"))
        eventLines.push(l.slice(5).replace(/^ /, ""));
    }
    while (!done) {
      const next = await reader.read();
      if (next.done) break;
      buffer += decoder.decode(next.value, { stream: true });
      if (buffer.length > 262144) throw Error("响应事件超过长度限制");
      let idx;
      while ((idx = buffer.indexOf("\n")) !== -1) {
        line(buffer.slice(0, idx));
        buffer = buffer.slice(idx + 1);
        if (done) break;
      }
    }
    if (!done) {
      buffer += decoder.decode();
      if (buffer) line(buffer);
      dispatch();
    }
    if (!done) throw Error("连接中断，当前回答可能不完整，请重试");
    if (finishReason === "length")
      throw Error("达到输出上限，当前回答不完整，可缩小问题后重试");
    if (finishReason && finishReason !== "stop")
      throw Error("模型未正常完成回答，请调整问题后重试");
    if (!total) throw Error("模型没有返回可显示的回答");
  } catch (e) {
    if (controller.signal.aborted)
      throw Error(timedOut ? "请求超时（120 秒），请重试" : "已停止生成");
    if (e instanceof TypeError)
      throw Error("无法连接 DeepSeek，请检查网络或浏览器跨域限制");
    // Only our own errors are displayed; never forward upstream response bodies.
    throw e;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", stop);
    if (reader) await reader.cancel().catch(() => {});
  }
}
