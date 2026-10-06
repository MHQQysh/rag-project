# 第 01 章 · 项目定位与个人贡献

[返回学习入口](README.md)

### Q001 · L1 · 用一分钟介绍这个项目。

<details>
<summary>展开答案与追问</summary>

**口述回答：** 这是基于开源 DeerFlow 的多轮 Agent 工作台。我把完整前后端部署到小规格云服务器，接入 DeepSeek API，配置 HTTPS 和登录入口，并新增独立的免注册演示账号。它能让模型调用工具完成任务并生成文件。

**原理与例子：** 一次请求可能经过多轮模型判断、工具执行、状态保存和流式回传。我的工作重点是部署适配、访问流程和可验证的工程改动；原有 Agent 引擎来自上游。

**追问与回答：** 你最有把握展示什么？展示一键演示登录、创建独立对话、调用 Python 生成文件，以及相应源码和验证记录。

**易错边界：** 不要说整个框架由我从零编写，也不要把未来计划算成已实现功能。

**源码 / 依据：** [README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/README.md)

</details>

### Q002 · L1 · 你为什么做这个项目？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 我希望把聊天模型变成能执行任务的网页应用，并实际理解从请求入口到工具结果落盘的完整链路。

**原理与例子：** 直接调用模型 API 只能覆盖模型服务；任务执行还涉及权限、文件、运行状态、失败恢复和部署资源。这个项目把这些工程问题连接起来。

**追问与回答：** 用户价值怎么验证？选择固定任务，看是否真的执行工具、产出正确文件并能下载，而不只看回答是否流畅。

**易错边界：** 学习动机可以讲，但不能虚构真实客户数量或商业转化。

**源码 / 依据：** [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md)

</details>

### Q003 · L1 · 它和普通 DeepSeek 聊天有什么区别？

<details>
<summary>展开答案与追问</summary>

**口述回答：** DeepSeek 在这里是模型服务，DeerFlow 是围绕模型构建的任务执行应用。后者负责会话、工具、沙箱、技能、状态和界面。

**原理与例子：** 例如问乘法时模型可以直接回答；要求执行 Python 并生成文件时，应用还需启动工具环境、运行代码、收集结果并提供下载。两种任务的工程路径不同。

**追问与回答：** 是不是普通聊天产品都没有工具？不是，比较的是本项目的组件职责，不能笼统否定其他产品能力。

**易错边界：** 不要把模型、Agent 框架和面向用户的 App 混为一谈。

**源码 / 依据：** [AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/AGENTS.md)

</details>

### Q004 · L1 · 你的个人贡献具体有哪些？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 可核对的贡献包括原版云端部署、DeepSeek 配置、小内存资源限制、沙箱启动等待调整、HTTPS 与首页跳转、独立演示登录，以及代码归档和讲解材料。

**原理与例子：** 面试时按“遇到的问题—修改文件—验证结果”讲。例如冷启动超时定位到 readiness 等待预算，演示登录则涉及前端按钮、认证路由、Cookie 和权限校验。

**追问与回答：** 能展示代码差异吗？看部署目录、demo.py、登录页组件及提交历史，而不是只展示运行截图。

**易错边界：** 不把上游多 Agent、长期记忆或 LangGraph 的实现算成个人原创。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md)

</details>

### Q005 · L2 · 使用开源项目有什么技术含量？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 价值在于理解系统边界、解决真实部署与集成问题，并能说明方案的代价。只换名字和截图的说服力有限，能定位故障并提供验证证据更有价值。

**原理与例子：** 本项目的小内存沙箱问题同时涉及启动预算、内存限制、IO 和服务健康；公开演示又涉及身份隔离、共享数据说明和认证接口。

**追问与回答：** 如何证明你不是只会部署？现场跟踪一条请求、解释相关函数，再说明自己改动如何进入这条链路。

**易错边界：** 不要为了强调难度编造重构规模或性能提升百分比。

**源码 / 依据：** [docs/plans/2026-10-06-demo-login-design.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/docs/plans/2026-10-06-demo-login-design.md)

</details>

### Q006 · L2 · 为什么同一个仓库里放 RAG 和 DeerFlow？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 它们是并列子项目：已有 RAG 子项目研究知识检索，DeerFlow 子项目保存完整 Agent 应用。主仓库统一展示入口，子目录各自管理依赖和启动流程。

**原理与例子：** 同仓库便于展示相互关系，但不会自动形成运行时集成。DeerFlow 若要使用另一个 RAG 后端，还需要明确工具或 API 接口。

**追问与回答：** 21 个 Star 属于谁？属于主仓库，不代表新增 DeerFlow 子项目单独获得了这些 Star。

**易错边界：** 不能把目录放在一起说成已经打通数据和权限。

**源码 / 依据：** [README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/README.md)

</details>

### Q007 · L2 · 你怎样在简历里准确描述它？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 可以写“基于开源 DeerFlow 完成 DeepSeek API 接入与云端部署，新增免注册演示入口，完成角色限制、流式会话及工具产物链路验证”。

**原理与例子：** 用动词对应可定位的改动：配置、部署、扩展、验证。后面补一个真实故障案例，效果比堆技术名词更清楚。

**追问与回答：** 可以写高并发平台吗？当前没有高并发压测证据，不能这样写。可写单实例部署和资源约束下的取舍。

**易错边界：** 建议表述不是已发生的业务业绩；不填编造的 QPS、DAU、营收或准确率。

**源码 / 依据：** [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md)

</details>

### Q008 · L2 · 你做得最难的一件事是什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 可以讲小规格服务器上沙箱冷启动导致任务失败：我先分离模型请求和容器启动，再检查资源与 readiness，最后调整等待预算和并发配置，并用实际代码执行验收。

**原理与例子：** 困难在于页面能打开不代表工具链能用。需要沿模型、Gateway、Docker、文件目录逐层判断，不把所有慢请求都归因于模型。

**追问与回答：** 结果如何？已有一次实际执行 17×19、生成 result.txt 并下载校验为 323 的记录；它不是性能基准。

**易错边界：** 只复述有记录的排查步骤，不给出未经统计的根因占比。

**源码 / 依据：** [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md)

</details>

### Q009 · L3 · 如果面试官说“这不是你的项目”，怎么回应？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 我会明确上游归属，并把讨论转回我负责的部署适配和功能扩展。框架不是我原创，但这些改动的实现、风险和验证可以逐项解释。

**原理与例子：** 带着源码差异回答：演示路由为何只允许固定普通用户，为什么重启不覆盖数据库，为什么 Pages 不能运行完整后端。责任边界清晰比夸大更可靠。

**追问与回答：** 如果让你从零实现最小版本？先做单用户模型调用、工具循环和状态存储，再逐步加认证、异步运行与沙箱。

**易错边界：** 不要把“基于开源”当缺点藏起来，也不要把上游作者的工作据为己有。

**源码 / 依据：** [README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/README.md)

</details>

### Q010 · L3 · 目前哪些能力尚不能承诺？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 不能承诺公网始终可达、高并发、多租户生产隔离或所有第三方工具可用。实际配置关闭了部分功能，公网也曾出现备案拦截。

**原理与例子：** “仓库中有代码”“部署中启用”“通过端到端验证”是三个不同层次。回答时分别说明，避免用代码存在替代效果证据。

**追问与回答：** 下一步先做什么？先解决可访问性并定义验收任务，再做限额、独立访客空间和稳定性测试。

**易错边界：** 演示共享账号不是完善的生产多租户系统。

**源码 / 依据：** [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>
