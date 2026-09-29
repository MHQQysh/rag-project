import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import initSqlJs from "sql.js";
import {
  parameters,
  referenceRows,
  validateRows,
  decompose,
  guardSQL,
  STANDARD_SQL,
} from "../core.mjs";
const raw = JSON.parse(
  await readFile(new URL("../assets/raw.json", import.meta.url)),
);
const fixtures = JSON.parse(
  await readFile(new URL("../assets/expected.json", import.meta.url)),
);
const SQL = await initSqlJs();
for (const fixture of fixtures)
  test(`Python parity ${fixture.params.region} ${fixture.params.current_start}`, async () => {
    const expected = referenceRows(raw, fixture.params);
    validateRows(expected, fixture.rows);
    const db = new SQL.Database(
      await readFile(new URL("../assets/synthetic.sqlite", import.meta.url)),
    );
    db.run("PRAGMA query_only=ON");
    const stmt = db.prepare(guardSQL(STANDARD_SQL));
    stmt.bind(
      Object.fromEntries(
        Object.entries(fixture.params).map(([k, v]) => [`:${k}`, v]),
      ),
    );
    const rows = [];
    while (stmt.step()) rows.push(stmt.getAsObject());
    stmt.free();
    db.close();
    validateRows(rows, expected);
    const a = decompose(rows),
      b = fixture.analysis;
    for (const key of [
      "totals",
      "factors",
      "permutations",
      "delta_cents",
      "reconciliation_cents",
      "imputation_notes",
    ])
      assert.deepEqual(a[key], b[key]);
  });
test("incorrect dates, fanout, duplicate channels and noninteger money fail", () => {
  const rows = structuredClone(fixtures[3].rows);
  for (const modify of [
    (r) => r[0].paid_cents++,
    (r) => (r[0].refund_cents = 0.1),
    (r) => (r[0] = { ...r[1] }),
    (r) => r.pop(),
    (r) => (r[0].order_count = true),
  ]) {
    const copy = structuredClone(rows);
    modify(copy);
    assert.throws(() => validateRows(copy, rows));
  }
});
test("SQL gate blocks mutation, system access and multiple statements", () => {
  for (const sql of [
    "DELETE FROM orders",
    "SELECT 1; SELECT 2",
    "WITH x AS (SELECT 1) DELETE FROM orders",
    "PRAGMA query_only=OFF",
    "SELECT * FROM sqlite_master",
    "SELECT randomblob(999999999)",
    "SELECT 1; /*x*/ DROP TABLE orders",
  ])
    assert.throws(() => guardSQL(sql));
  assert.equal(
    guardSQL("SELECT ';' AS value; -- comment"),
    "SELECT ';' AS value; -- comment",
  );
});
test("scope and zero order edge cases", () => {
  assert.throws(() => parameters("2026-09", "华东"));
  assert.throws(() => parameters("2026-08", "华南"));
  assert.throws(() =>
    decompose(
      fixtures[0].rows.map((r) => ({ ...r, order_count: 0, paid_cents: 0 })),
    ),
  );
  const rows = structuredClone(fixtures[3].rows);
  for (const r of rows)
    if (r.channel === "自营" && r.period === "current") {
      r.order_count = 0;
      r.paid_cents = 0;
    }
  const a = decompose(rows);
  assert.ok(a.imputation_notes.length);
  assert.equal(a.reconciliation_cents, 0);
});
test("cross-month successful refunds include older paid orders", () => {
  const r = referenceRows(
    {
      channels: [{ channel_id: 1, name: "渠道" }],
      orders: [
        {
          order_id: 1,
          channel_id: 1,
          shipping_region: "华东",
          paid_at: "2026-06-01",
          status: "paid",
          paid_cents: 10000,
        },
      ],
      refunds: [
        {
          order_id: 1,
          refunded_at: "2026-08-01",
          status: "success",
          amount_cents: 500,
        },
        {
          order_id: 1,
          refunded_at: "2026-08-02",
          status: "failed",
          amount_cents: 1000,
        },
      ],
    },
    parameters("2026-08", "华东"),
  );
  assert.equal(r[1].refund_cents, 500);
  assert.equal(r[1].order_count, 0);
});
