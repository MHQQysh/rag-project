import { mkdir, copyFile } from "node:fs/promises";
await mkdir("vendor", { recursive: true });
for (const file of ["sql-wasm.js", "sql-wasm.wasm"])
  await copyFile(`node_modules/sql.js/dist/${file}`, `vendor/${file}`);
await copyFile("node_modules/sql.js/LICENSE", "vendor/sql.js-LICENSE");
