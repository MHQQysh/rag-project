import test from "node:test";
import assert from "node:assert/strict";
import { generateSQL } from "../model.mjs";
const base = {
  key: "test-token-not-a-real-key",
  schema: "orders",
  params: { region: "华东" },
};
test("only fixed official origin receives credential; evidence return does not contain it", async () => {
  let request;
  const r = await generateSQL({
    ...base,
    fetcher: async (url, init) => {
      request = { url, init };
      return {
        ok: true,
        json: async () => ({
          choices: [{ message: { content: '{"sql":"SELECT 1"}' } }],
          model: "test",
        }),
      };
    },
  });
  assert.equal(request.url, "https://api.deepseek.com/chat/completions");
  assert.equal(request.init.headers.Authorization, `Bearer ${base.key}`);
  assert.equal(r.sql, "SELECT 1");
  assert.ok(!JSON.stringify(r).includes(base.key));
});
test("no key, HTTP errors and malformed results fail without fallback", async () => {
  await assert.rejects(generateSQL({ ...base, key: "" }));
  for (const status of [401, 402, 429, 500])
    await assert.rejects(
      generateSQL({ ...base, fetcher: async () => ({ ok: false, status }) }),
    );
  await assert.rejects(
    generateSQL({
      ...base,
      fetcher: async () => ({
        ok: true,
        json: async () => ({ choices: [{ message: { content: "not-json" } }] }),
      }),
    }),
  );
});
