import { test } from "node:test";
import assert from "node:assert/strict";
import {
  chunkDocument,
  retrieve,
  buildMessages,
  exportConversation,
} from "../core.mjs";
test("chunks cover text, overlap and stay bounded", () => {
  const text = "分块测试 alpha beta。".repeat(300);
  const chunks = chunkDocument("课件.md", text);
  assert.ok(chunks.length > 5);
  assert.ok(chunks.every((c) => c.text.length <= 900));
  assert.equal(chunks[0].text.slice(-120), chunks[1].text.slice(0, 120));
  assert.ok(chunks.at(-1).text.endsWith("beta。"));
  assert.equal(chunkDocument("empty", "  ").length, 0);
});
test("Chinese and English retrieval finds relevant source, no fabricated match", () => {
  const chunks = [
    ...chunkDocument("甲", "上下文压缩用于控制历史消息长度。"),
    ...chunkDocument("乙", "Embedding represents text as vectors."),
  ];
  assert.equal(retrieve("上下文压缩", chunks)[0].name, "甲");
  assert.equal(retrieve("vectors", chunks)[0].name, "乙");
  assert.deepEqual(retrieve("zzzz", chunks), []);
});
test("history and documents bounded and clearly untrusted", () => {
  const hits = retrieve("测试", chunkDocument("资料", "测试".repeat(9000)));
  const messages = buildMessages(
    Array.from({ length: 40 }, () => ({
      role: "user",
      content: "a".repeat(2000),
    })),
    "测试",
    hits,
    true,
  );
  assert.ok(messages.reduce((n, m) => n + m.content.length, 0) < 24000);
  assert.ok(messages[0].content.includes("不可信"));
  assert.ok(messages.at(-1).content.includes("[S1]"));
  assert.ok(
    buildMessages([], "找答案", [], true).at(-1).content.includes("没有命中"),
  );
});
test("export keeps per-turn provenance and completion status without arbitrary metadata", () => {
  const output = exportConversation([
    {
      query: "Q",
      answer: "partial",
      model: "test",
      outcome: "已停止生成",
      key: "must-not-export",
      hits: [{ id: "S1", name: "课程.md", index: 2, text: "原文" }],
    },
  ]);
  assert.ok(output.includes("已停止生成"));
  assert.ok(output.includes("[S1] 课程.md · 第 2 块"));
  assert.ok(output.includes("原文"));
  assert.ok(!output.includes("must-not-export"));
});
