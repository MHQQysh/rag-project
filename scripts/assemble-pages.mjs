import { mkdir, copyFile, writeFile, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "db-gpt-commerce/web/dist");
await readFile(path.join(dist, "db-gpt-commerce/index.html")); // Commerce must already be built.
await mkdir(path.join(dist, "deerflow-web"), { recursive: true });
for (const file of [
  "index.html",
  "styles.css",
  "theme.css",
  "core.mjs",
  "model.mjs",
  "app.mjs",
  "guide.html",
])
  await copyFile(
    path.join(root, "deerflow-web", file),
    path.join(dist, "deerflow-web", file),
  );
await mkdir(path.join(dist, "deerflow-interview"), { recursive: true });
for (const file of ["index.html", "print.html"]) {
  await copyFile(
    path.join(root, "deerflow/docs/interview", file),
    path.join(dist, "deerflow-interview", file),
  );
}
await writeFile(
  path.join(dist, "index.html"),
  `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAG Project · 项目工作台</title><style>body{font:16px/1.9 system-ui,sans-serif;background:#f4f6ef;color:#294434;max-width:900px;margin:70px auto;padding:25px}h1{font-size:38px}p{color:#77846c}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:22px}a.card{display:block;border:1px solid #d8e1cc;background:white;border-radius:14px;padding:28px;color:inherit;text-decoration:none}a.card:hover{border-color:#567949}h2{font-size:22px}small{color:#839276}footer{margin-top:35px;font-size:13px}a{color:#426b37}</style></head><body><small>RAG PROJECT / BROWSER WORKSPACES</small><h1>选择一个工作台，开始探索。</h1><p>从静态工作台到完整 Agent 源码，再到 120 道项目面试题解。按你的目标选择入口。</p><div class="cards"><a class="card" href="./deerflow-web/"><small>01 / DEERFLOW WEB</small><h2>文档与思考工作台 ↗</h2><p>流式聊天、本地资料检索、来源核对与架构讲解。</p></a><a class="card" href="./db-gpt-commerce/"><small>02 / COMMERCE ANALYSIS</small><h2>电商经营分析 ↗</h2><p>从公开模拟数据出发，分析收入变化并核对贡献因素。</p></a><a class="card" href="./deerflow-interview/"><small>03 / INTERVIEW FIELD GUIDE</small><h2>120 道项目面试题解 ↗</h2><p>架构、Agent、RAG、部署与演示登录。带答案、追问、源码定位和练习筛选。</p></a><a class="card" href="https://github.com/MHQQysh/rag-project/tree/main/deerflow"><small>04 / ORIGINAL DEERFLOW</small><h2>完整 Agent 项目源码 ↗</h2><p>保留原版前后端、工具、沙箱和个人部署改动。应用由 ECS 运行，访问状态见部署说明。</p></a></div><footer><a href="https://github.com/MHQQysh/rag-project">查看完整源码与其他 RAG 子项目</a> · 静态工作台和面试文档由 Pages 发布；完整 Agent 需要后端服务。</footer></body></html>`,
);
console.log(
  "Pages artifact includes commerce, DeerFlow Web, interview reader and project navigation.",
);
