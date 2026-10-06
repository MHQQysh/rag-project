import { test } from "node:test";
import assert from "node:assert/strict";
import { streamChat } from "../model.mjs";
const delta = (s) =>
  "data: " +
  JSON.stringify({
    choices: [{ delta: { content: s }, finish_reason: null }],
  }) +
  "\r\n\r\n";
function response(s) {
  const bytes = new TextEncoder().encode(s);
  return new Response(
    new ReadableStream({
      start(c) {
        for (let i = 0; i < bytes.length; i += 3)
          c.enqueue(bytes.slice(i, i + 3));
        c.close();
      },
    }),
    { headers: { "Content-Type": "text/event-stream" } },
  );
}
const base = {
  key: "unit-test-key",
  model: "deepseek-flash",
  messages: [{ role: "user", content: "test" }],
};
test("SSE handles split UTF8 and CRLF and DONE", async () => {
  let text = "";
  let sent;
  await streamChat({
    ...base,
    onDelta: (d) => (text += d),
    fetchImpl: async (url, o) => {
      sent = { url, ...o };
      return response(
        ": ping\n\n" + delta("你好") + delta("世界") + "data: [DONE]\n\n",
      );
    },
  });
  assert.equal(text, "你好世界");
  assert.equal(sent.url, "https://api.deepseek.com/chat/completions");
  assert.equal(sent.redirect, "error");
  assert.ok(!sent.body.includes(base.key));
});
test("errors never echo server response or key", async () => {
  await assert.rejects(
    streamChat({
      ...base,
      fetchImpl: async () => new Response(base.key, { status: 401 }),
    }),
    /Key 无效/,
  );
});
test("truncated streams and empty responses are not success", async () => {
  await assert.rejects(
    streamChat({ ...base, fetchImpl: async () => response(delta("partial")) }),
    /中断/,
  );
  await assert.rejects(
    streamChat({
      ...base,
      fetchImpl: async () => response("data: [DONE]\n\n"),
    }),
    /没有返回/,
  );
});
test("abort and time budget terminate requests", async () => {
  const controller = new AbortController();
  controller.abort();
  const fetchImpl = async (u, { signal }) =>
    new Promise((r, j) => {
      if (signal.aborted) j(signal.reason);
      else
        signal.addEventListener("abort", () => j(signal.reason), {
          once: true,
        });
    });
  await assert.rejects(
    streamChat({ ...base, signal: controller.signal, fetchImpl }),
    /已停止/,
  );
  await assert.rejects(
    streamChat({ ...base, timeoutMs: 20, fetchImpl }),
    /超时/,
  );
});
