/* No credentials are passed to this disposable query worker. */
importScripts("./vendor/sql-wasm.js");
self.onmessage = async ({ data }) => {
  let db, statement;
  try {
    const { guardSQL } = await import("./core.mjs");
    guardSQL(data.sql);
    const SQL = await initSqlJs({ locateFile: (file) => `./vendor/${file}` });
    db = new SQL.Database(new Uint8Array(data.database));
    db.run("PRAGMA query_only=ON");
    // SQLite iterator verifies the statement boundary in addition to lexical checks.
    let count = 0;
    for (const stmt of db.iterateStatements(data.sql)) {
      count++;
      stmt.free();
    }
    if (count !== 1) throw Error("只允许一条查询");
    statement = db.prepare(data.sql);
    statement.bind(
      Object.fromEntries(
        Object.entries(data.params).map(([k, v]) => [`:${k}`, v]),
      ),
    );
    const names = statement.getColumnNames();
    if (new Set(names).size !== names.length) throw Error("输出列名重复");
    const rows = [];
    while (statement.step()) {
      if (rows.length >= 100) throw Error("结果超过 100 行");
      rows.push(statement.getAsObject());
    }
    self.postMessage({ rows });
  } catch (error) {
    self.postMessage({ error: String(error.message || error).slice(0, 600) });
  } finally {
    statement?.free();
    db?.close();
  }
};
