import { mkdir, copyFile, cp, writeFile, readFile } from "node:fs/promises";
await mkdir("dist/db-gpt-commerce", { recursive: true });
for (const file of [
  "index.html",
  "styles.css",
  "app.mjs",
  "core.mjs",
  "model.mjs",
  "query-worker.js",
])
  await copyFile(file, `dist/db-gpt-commerce/${file}`);
for (const folder of ["assets", "vendor"])
  await cp(folder, `dist/db-gpt-commerce/${folder}`, { recursive: true });
await mkdir("dist/db-gpt-commerce/guide", { recursive: true });
await cp("../docs/项目讲解", "dist/db-gpt-commerce/guide", {
  recursive: true,
  filter: (source) =>
    !source.endsWith(".py") && !source.includes("__pycache__"),
});
await writeFile("dist/.nojekyll", "");
await writeFile(
  "dist/index.html",
  '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=./db-gpt-commerce/"><title>RAG Project</title><p><a href="./db-gpt-commerce/">打开电商经营分析工作台</a></p></html>',
);
const source = await readFile("app.mjs", "utf8");
if (/localStorage|sessionStorage|document\.write|innerHTML/.test(source))
  throw Error("Unexpected unsafe storage or rendering in app");
console.log(
  "Static site built at dist/. Only browser app, synthetic assets and guide are published.",
);
