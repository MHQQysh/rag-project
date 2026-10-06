# DeerFlow Web Pages 设计

用户已确认纯 Pages 轻量版本，并授权连接 GitHub、上传和部署到当前仓库。

新增独立子项目 `deerflow-web`。原生浏览器 ES modules 实现用户自带 Key 的 DeepSeek 流式聊天、本地 TXT/Markdown 文档分块与关键词检索、带来源的回答、取消、Markdown 导出和架构说明。明确这是受 DeerFlow 启发的浏览器版，不宣称运行完整 Python/LangGraph/多 Agent/沙箱。

Key 仅存在当前页面内存，固定向 DeepSeek 官方 HTTPS 端点发送；不使用持久浏览器存储，不发送到 GitHub。文档在浏览器中分块检索，只发送选中的片段及限额对话。模型输出使用 textContent 呈现。最多 8 个文件、单文件 1 MiB、总计 4 MiB；限定扩展名和文本内容。检索使用英文词与中文双字词 BM25 风格评分，不宣称向量检索。

模块：core.mjs（纯分块检索与上下文预算）、model.mjs（HTTP/SSE/超时）、app.mjs（交互与状态）、styles.css/index.html（自适应界面）、guide.html（源码与逻辑说明）、tests（Node 单元和浏览器流程）。允许无 Key 的样例检索，但不伪造模型回答。

复用仓库现有 Pages 工作流，先构建 commerce，再把 deerflow-web 白名单静态文件加入同一 artifact。根页面提供两个入口；避免多个 Pages workflow 相互覆盖。保留现有 commerce URL。验证单元测试、浏览器交互、取消与无效 Key、密钥不落盘、移动端布局、部署 Actions 状态与线上 URL。
