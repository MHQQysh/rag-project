# DeerFlow Web

独立浏览器轻量版，受 DeerFlow 的工作台交互和源码学习需求启发；不是完整 DeerFlow 的官方移植。直接部署到 GitHub Pages，访问者在页面输入自己的 DeepSeek Key。

入口：仓库 Pages 地址下的 **`deerflow-web/`**，例如 https://mhqqysh.github.io/rag-project/deerflow-web/ （若账号配置自定义域名，GitHub 会跳转到对应域名）。

## 使用

1. 打开网页，输入自己的 DeepSeek Key，选择 Flash 或 Pro。
2. 直接提问，或添加 UTF-8 TXT/Markdown（最多 8 个、每个 1 MiB、合计 4 MiB）。
3. “只看检索”不调用模型、不需要 Key；“发送”会把问题、有限历史与命中片段发给 DeepSeek。
4. 支持流式显示、取消、原文核对和 Markdown 导出。刷新会清除所有本页数据。

不支持 PDF/Word、向量检索、联网搜索、任意代码执行、多 Agent、服务端长期记忆。回答显示为安全纯文本（保留 Markdown 原文），导出为 .md。

## 代码

| 文件                                | 职责                                                                |
| ----------------------------------- | ------------------------------------------------------------------- |
| core.mjs                            | 900 字符分块、120 重叠、中文双字词/英文词 BM25 风格检索、上下文预算 |
| model.mjs                           | 固定 DeepSeek HTTPS 接口，SSE、UTF-8 分片、120 秒超时和取消         |
| app.mjs                             | 页面状态、上传限制、对话、来源与导出                                |
| index.html / styles.css / theme.css | 自适应交互界面                                                      |
| guide.html                          | 架构、源码与具体运行逻辑讲解                                        |
| tests/                              | Node 测试                                                           |

Key 只存在页面内存，请求固定发给官方 API。不会写入仓库、浏览器持久存储、导出或 URL。原始文档不上传 GitHub；检索片段会交给 DeepSeek。浏览器检索和模型引用不是事实正确性的保证。

## 本地查看与测试

在本目录运行 `node --test tests/*.test.mjs`。从仓库根目录运行 `python -m http.server 8080`，打开 `http://localhost:8080/deerflow-web/`。ES 模块需要 HTTP 服务，不建议直接双击 HTML。

## 发布

复用 `.github/workflows/commerce-pages.yml`，构建两个子项目后上传同一份 artifact，避免单仓库多 Pages 部署覆盖彼此。`scripts/assemble-pages.mjs` 仅复制此项目白名单静态文件并生成项目入口页。无需新增服务器、GitHub Secret 或全局模型 Key。

完整 DeerFlow 仍需独立后端：[上游源码](https://github.com/bytedance/deer-flow)。本子项目没有复制本机配置、私有会话或上游仓库全部源码。
