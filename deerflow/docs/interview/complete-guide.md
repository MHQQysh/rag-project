# DeerFlow × RAG：先把整条逻辑讲明白

> 阅读基线：2026-10-06 导入的个人部署版本。这里区分上游实现、当前配置、实际验收和后续设计；它们不是同一个完成标准。

## §0 可以这样介绍这个项目

**DeerFlow Agent 工作台｜基于开源框架的部署与功能扩展**

**技术栈：** Next.js / React · FastAPI · LangGraph · DeepSeek API · Tool Calling · Docker 沙箱 · SSE · SQLite · Redis · Nginx。

- **目标：** 将模型问答扩展为可执行任务的网页工作台，支持多会话、工具调用、文件产物和可追踪的任务过程。
- **原版架构：** Lead Agent 负责决策，通过工具执行动作、委派子任务；中间件负责上下文、记忆、压缩和保护；运行时负责状态、事件和持久化。
- **个人改动：** 完成小规格 ECS 部署与 DeepSeek 配置，调整沙箱启动等待和资源策略，配置 HTTPS、登录入口与独立普通演示用户的一键登录。
- **验证证据：** 记录了认证与权限回归、前端检查与构建，以及实际执行 Python、生成文件并下载校验的任务。没有把单次成功当成性能基准。
- **作品组织：** 完整源码置于已有 RAG 仓库的 `deerflow/`，题解可以在 GitHub Pages 阅读，完整应用在 ECS 运行。

这是可供理解后使用的介绍模板。不要把上游框架说成个人从零研发，不要填写没有测量过的性能提升、业务规模或客户数据。

## §1 三个概念先分开

| 层次 | 在本项目中是什么 | 负责什么 |
| --- | --- | --- |
| 模型 | DeepSeek API | 根据输入生成回答、工具调用等输出 |
| Harness | DeerFlow 的核心执行包 | 围绕模型组织工具、状态、子任务、记忆和执行约束 |
| App | 前端、Gateway、登录和部署服务 | 让用户通过网页创建会话、发起任务、查看产物 |

可以把模型看作决策来源，工具看作可执行动作，框架负责把决策变成受控执行，网页负责把这个过程交给用户。模型本身不会因为说出“我已生成文件”，就让服务器上真的出现文件。

## §2 一次请求的完整路径

```text
用户输入 / 附件
  ↓
Next.js 页面：确定 thread，提交输入，展示状态
  ↓ HTTPS，同一域名
Nginx：前端 / API 路由，TLS，流式代理
  ↓
FastAPI Gateway：认证、资源权限、参数校验、创建 run
  ↓
RunManager + run_agent：组织执行与事件
  ↓
Lead Agent ⇄ DeepSeek API
  ├─ 直接形成最终回答
  ├─ 调工具 → 沙箱 / 搜索 / 文件 → 工具结果回到模型
  └─ 委派子 Agent → 子任务结果回到主 Agent
  ↓
状态与 checkpoint / 运行事件 / 文件产物分别保存
  ↓ SSE + 授权文件接口
前端合并消息、更新任务卡片、展示可下载产物
```

**例子：** 用户要求“用 Python 计算 17×19，并生成 result.txt”。首先创建一次 run；模型选择命令工具；沙箱执行代码并写文件；工具返回真实结果；Agent 解释结果并呈现文件；最终验收既要检查回答，也要下载文件确认内容为 `323`。

**关键区别：** thread 是一段会话，run 是其中一次执行，模型调用是执行中的一个步骤。用户的一条问题可能触发多次模型调用和多个工具动作。刷新网页主要是恢复观察，不应默认重新执行任务。

## §3 代码从哪里读

以下路径以 `deerflow/` 为根。按这条顺序阅读，先找输入输出，再深入内部实现。

| 顺序 | 文件或目录 | 阅读时回答的问题 |
| --- | --- | --- |
| 1 | `frontend/src/core/threads/hooks.ts` | 输入如何提交，流如何影响界面？ |
| 2 | `backend/app/gateway/app.py` | 服务启动时装了哪些路由与依赖？ |
| 3 | `backend/app/gateway/routers/thread_runs.py` | 身份和 thread 如何变成一次 run？ |
| 4 | `backend/packages/harness/deerflow/runtime/runs/` | 谁启动、取消、记录执行？ |
| 5 | `backend/packages/harness/deerflow/agents/lead_agent/agent.py` | 模型、工具、中间件怎样组装？ |
| 6 | `backend/packages/harness/deerflow/agents/middlewares/` | 上下文在哪里注入、压缩或保护？ |
| 7 | `backend/packages/harness/deerflow/subagents/` | 子任务如何获得输入并返回结果？ |
| 8 | `backend/packages/harness/deerflow/sandbox/tools.py` | 工具如何操作真实环境？ |
| 9 | `backend/packages/harness/deerflow/persistence/` | 哪些状态持久化，怎样查回？ |
| 10 | `deploy/ecs/` | 代码在当前服务器上怎样运行？ |

核心依赖方向是 app 使用 harness，harness 不反向依赖 app。网页、IM 等入口可以复用执行能力，而核心执行不必认识 FastAPI 的 Request 对象。

## §4 个人改动如何映射到源码

| 改动 | 位置 | 解决的问题与边界 |
| --- | --- | --- |
| 演示身份校验 | `backend/app/gateway/auth/demo.py` | 只允许服务器指定的无密码普通用户；关闭后拒绝演示请求 |
| 演示认证路由 | `backend/app/gateway/routers/auth.py` | 查询入口状态、签发正常认证 cookie，不向浏览器传管理员密码 |
| 请求保护 | `backend/app/gateway/auth_middleware.py`、`backend/app/gateway/csrf_middleware.py` | 明确公共登录路径并限制演示身份管理操作 |
| 页面入口 | `frontend/src/components/auth/demo-login.tsx` | 一键进入、错误状态和共享数据提示 |
| 沙箱等待 | `backend/packages/harness/deerflow/community/aio_sandbox/backend.py` | readiness 等待 60→180 秒，适应冷启动；不是提升 CPU 性能 |
| 部署配置 | `deploy/ecs/` | 生产构建、服务管理、TLS、资源限制和并发取舍 |

认证相关回归记录为 183 项通过，演示按钮交互记录为 3 项通过；前端检查与生产构建通过。全量后端套件没有完整跑完，不能用中途通过数量替代完整通过结论。详细口径保存在部署文档。

## §5 当前能说到什么程度

| 类别 | 当前结论 |
| --- | --- |
| 源码完整性 | 保留完整可追踪前后端、核心包、技能和测试；运行密钥、数据库和依赖需自行配置 |
| 多会话 | 原版具有多会话能力；不等于小机器支持无限并发执行 |
| 演示入口 | 独立普通用户，无需访客注册；不同演示访客共享历史和文件 |
| 资源配置 | 子任务运行并发 1、模型调用并发 2；局部限制不等于全站统一配额 |
| 沙箱 replicas | 暖池目标与软上限相关配置，不能宣称为全局活动容器硬上限 |
| 记忆 | 当前 DeerMem + FTS5；不声称所有用户隔离边界均已完成生产审计 |
| 上传 / 视觉 | 上传不等于自动 RAG；视觉声明不等于端到端验收，真实模型与请求格式仍需验证 |
| RAG 集成 | RAG 与 DeerFlow 同仓库存放，尚未接通统一检索工具和权限 |
| 其他开关 | 定时调度、批量子任务和部分扩展能力在当前配置中关闭 |
| 公网访问 | 曾观察到阿里云备案拦截及连接重置；服务器内成功不等于所有访客都能打开 |

## §6 三分钟面试讲述顺序

**第一分钟讲目标与架构。** 先解释为什么模型 API 外面还需要任务执行层，再沿页面、Gateway、Agent、工具、状态、事件讲一遍。用生成文件的例子贯穿，不要只报技术名词。

**第二分钟讲自己的改动。** 选演示登录或沙箱冷启动一个问题，说清现象、定位证据、修改位置和取舍。演示登录复用原认证体系，创建普通身份，而不是公开自己的账号密码。

**第三分钟讲验证与不足。** 给出测试和文件验收证据，主动说明共享演示空间、资源限制与公网接入状态。下一步先补隔离、额度和可重复评估，再接入 RAG 检索工具。

## §7 七天学习路径

1. **第 1 天：** 读本总述和第 1—2 章，能画出架构并区分模型、框架与 App。
2. **第 2 天：** 读第 3—4 章，跟踪一条请求，解释 thread、run、模型与工具循环。
3. **第 3 天：** 读第 5—6 章，找到工具和子 Agent 入口，解释隔离、排队和资源限制。
4. **第 4 天：** 读第 7—8 章，区分历史、摘要、记忆与 RAG，能讲一个检索失败案例。
5. **第 5 天：** 读第 9—10 章，解释事件流、状态恢复、持久化和测试范围。
6. **第 6 天：** 读第 11—12 章，讲部署与演示登录的真实实现和风险边界。
7. **第 7 天：** 隐藏答案，随机抽题，每题先讲 60 秒，再回答一个追问，最后定位源码。

每题都按“口述回答 → 原理与例子 → 追问与回答 → 易错边界 → 源码”组织。L1 是基础口述，L2 要理解工程取舍，L3 要能分析边界与改进方案。建议先练 48 道 L1，再逐步覆盖全部 120 道。


## §8 项目定位与个人贡献

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


## §9 总体架构与代码导航

### Q011 · L1 · 整体架构如何分层？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 浏览器中的 Next.js 负责界面，Nginx 负责统一入口，FastAPI Gateway 负责认证和请求协调，harness 包负责 Agent 执行，模型 API 与沙箱提供外部能力。

**原理与例子：** 数据持久化、事件流和文件系统横跨执行过程。按职责划分后，可以判断错误发生在页面、网络入口、请求处理、模型调用还是工具环境。

**追问与回答：** 端口怎么对应？当前前端 3000、Gateway 8001，公共 HTTPS 443；内部端口不需要直接暴露给访客。

**易错边界：** 这些端口是当前部署配置，不是协议规定。

**源码 / 依据：** [AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/AGENTS.md)

</details>

### Q012 · L1 · backend/app 与 backend/packages/harness 有何区别？

<details>
<summary>展开答案与追问</summary>

**口述回答：** app 层处理 HTTP、认证和渠道接入；harness 层封装 Agent、工具、记忆、模型及运行时。这样核心执行能力可以被不同入口复用。

**原理与例子：** 如果把 FastAPI Request 对象直接塞进核心工具，核心层就会绑定 Web 框架。通过明确的运行上下文和接口传递身份，更容易测试和扩展。

**追问与回答：** 新增一个 HTTP 路由放哪里？通常放 app/gateway/routers；通用 Agent 能力放 harness。

**易错边界：** 分层是实际代码组织，不意味着两者完全不存在依赖耦合。

**源码 / 依据：** [backend/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/AGENTS.md)

</details>

### Q013 · L1 · 前端重点看哪些目录？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 看 app 下的页面路由、components 下的界面组件、core 下的业务状态和 API 逻辑。对话流程重点是 core/threads，认证重点是 core/auth。

**原理与例子：** 页面组件描述界面，业务 hook 连接后端、合并状态并触发更新。不要只读聊天框组件就认为已经理解发送请求的全部逻辑。

**追问与回答：** 登录页在哪里？frontend/src/app/(auth)/login/page.tsx，演示按钮独立在 components/auth/demo-login.tsx。

**易错边界：** Next.js 路由组括号用于组织目录，不会作为 URL 路径段。

**源码 / 依据：** [frontend/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/AGENTS.md)

</details>

### Q014 · L1 · 从哪里开始读后端代码？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先看 Gateway 的 app.py 了解启动与路由，再看 threads、thread_runs 和认证路由，最后进入 lead_agent/agent.py 看模型、工具与 middleware 如何组装。

**原理与例子：** 这样先掌握入口和边界，再深入执行，比按文件名从头顺序阅读更容易建立因果链。每一步都记录输入、输出及状态存放位置。

**追问与回答：** 只剩半小时看什么？读架构指南、一个登录接口和一次 run 创建流程，画出请求路径。

**易错边界：** 不要把文档中的简化图当成全部真实调用关系。

**源码 / 依据：** [backend/app/gateway/app.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/app.py)

</details>

### Q015 · L2 · 配置文件和环境变量各负责什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 配置文件描述模型、工具、存储与策略；环境变量提供密钥和部署位置等运行参数。配置中的 $DEEPSEEK_API_KEY 在启动解析时引用环境变量。

**原理与例子：** 模板可以进入 Git，实际配置和密钥文件留在部署机器。这样既能审查配置结构，也避免把密钥复制进仓库历史。

**追问与回答：** 变量缺失怎么办？应明确报错并检查服务实际加载的环境，而不是静默使用错误模型。

**易错边界：** 环境变量本身不是加密保险箱，仍需限制文件和进程访问。

**源码 / 依据：** [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml) · [deploy/ecs/model.env.example](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/model.env.example) · [deploy/ecs/runtime.env.example](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/runtime.env.example)

</details>

### Q016 · L2 · 为什么需要 Nginx？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 它把前端、API 和流式接口统一到同一个域名，并负责 TLS、请求转发、上传限制和超时设置。

**原理与例子：** 浏览器访问同源 /api 路径，部署时更容易管理 Cookie 与跨域策略。流式响应还需要关闭不合适的代理缓冲，避免内容攒到最后才显示。

**追问与回答：** 能不用 Nginx 吗？可以换其他反向代理，但这些职责仍要有人承担。

**易错边界：** 有 Nginx 不代表自动具备鉴权、限流或高可用。

**源码 / 依据：** [deploy/ecs/public-entry.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/public-entry.conf)

</details>

### Q017 · L2 · LangGraph 服务是不是另外启动了一个进程？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 当前部署由 Gateway 内嵌运行 LangGraph 兼容执行逻辑，不应按旧架构凭空补一个独立 LangGraph 服务。

**原理与例子：** Nginx 将 /api/langgraph/ 前缀改写到 Gateway 的 /api/，前端 SDK 仍能使用兼容接口。这是外部接口形状与内部部署拓扑的区别。

**追问与回答：** 如何确认？看 systemd 的 ExecStart、Nginx upstream 和 Gateway 启动代码。

**易错边界：** 不同 DeerFlow 版本拓扑可能不同，面试要绑定自己部署的源码版本。

**源码 / 依据：** [deploy/ecs/deerflow-gateway.service](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/deerflow-gateway.service)

</details>

### Q018 · L2 · 为什么不能只复制 frontend 就得到完整应用？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 前端需要后端提供会话、认证、模型配置、运行任务和文件服务。静态页面能呈现界面，但不能替代这些服务。

**原理与例子：** 即使让浏览器直接调用模型，也只是重新做了一套浏览器应用，服务端沙箱与持久化语义并不会自动出现。

**追问与回答：** 什么时候可以单独部署前端？前端能访问一个兼容后端，且域名、Cookie 和跨域配置正确时。

**易错边界：** 本项目没有把完整 Agent 后端放进 GitHub Pages。

**源码 / 依据：** [frontend/src/core/config/index.ts](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/core/config/index.ts)

</details>

### Q019 · L3 · 如何避免模块之间形成循环依赖？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 优先通过小接口和职责边界解决；确有启动顺序问题时，再使用局部导入，避免模块导入时拉起整个执行系统。

**原理与例子：** 例如状态定义应尽量只依赖数据类型，不应顺便初始化工具执行器。循环依赖往往是职责混杂的信号，局部导入只能缓解，不能代替设计。

**追问与回答：** 怎么测试？用最小导入测试和独立工厂测试，确认导入本身不会访问网络或启动容器。

**易错边界：** 不要宣称本项目所有循环依赖都已消除。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/thread_state.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/thread_state.py)

</details>

### Q020 · L3 · 怎样评估一个新功能应改哪些层？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先写清用户动作、HTTP 契约、身份边界、核心执行和状态变化，再把每一步映射到代码模块。

**原理与例子：** 演示登录就是例子：按钮负责交互，路由签发会话，middleware 控制权限，部署环境指定账号，测试验证正常与拒绝路径。

**追问与回答：** 只改前端能限制权限吗？不能。前端隐藏按钮是体验，服务端校验才是执行边界。

**易错边界：** 不要为了小功能同时重构不相关的框架层。

**源码 / 依据：** [docs/plans/2026-10-06-demo-login-design.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/docs/plans/2026-10-06-demo-login-design.md)

</details>


## §10 请求、会话与运行状态

### Q021 · L1 · 用户发送一句话后发生什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 前端提交输入和会话信息，Gateway 校验身份与请求，创建运行任务，执行 Agent；Agent 调模型并按需调用工具，结果以事件流返回，最终状态和产物保存。

**原理与例子：** 这一过程可能持续多个模型回合，因此 HTTP 请求、后台 run 和聊天 thread 不能视为同一对象。理解这三者能解释断线重连和历史恢复。

**追问与回答：** 浏览器关闭是否一定停止任务？不一定，取决于运行管理和断连策略，不能仅凭页面关闭推断。

**易错边界：** 具体断连行为需要检查请求参数与当前 runtime。

**源码 / 依据：** [backend/app/gateway/routers/thread_runs.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/routers/thread_runs.py)

</details>

### Q022 · L1 · thread_id 和 run_id 有什么区别？

<details>
<summary>展开答案与追问</summary>

**口述回答：** thread_id 标识持续的对话容器，run_id 标识其中一次执行。一个会话通常会产生多次运行，每次运行可能包含多个模型与工具步骤。

**原理与例子：** 用户连续追问会复用 thread，但产生新 run。日志中同时记录二者，才能把单次失败和整段会话关联起来。

**追问与回答：** 一个 run 就一次模型请求吗？不是，Agent 的一个 run 可以调用模型多次。

**易错边界：** 不要用消息数量代替模型调用次数。

**源码 / 依据：** [backend/app/gateway/routers/thread_runs.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/routers/thread_runs.py)

</details>

### Q023 · L1 · 新建多个对话会混在一起吗？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 正常设计以用户和 thread 共同隔离状态及文件。新对话使用不同标识，读取资源时还必须验证当前用户是否有权访问。

**原理与例子：** 随机 UUID 只能降低猜中的概率，不构成授权。即使知道别人的 thread_id，服务端仍应拒绝读取其消息和产物。

**追问与回答：** 演示访客为什么能看到相同历史？因为他们有意共用同一个演示身份，而不是隔离机制失效。

**易错边界：** 共享演示账号与独立访客账号是不同产品方案。

**源码 / 依据：** [backend/app/gateway/routers/threads.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/routers/threads.py)

</details>

### Q024 · L1 · 项目和对话有什么区别？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 项目用于组织相关对话以及项目级说明、资料等；对话承载具体交流，run 承载一次执行。

**原理与例子：** 可以把项目理解为任务背景的组织单位，把 thread 理解为连续工作记录。项目并不等于一个独立部署的应用。

**追问与回答：** 子项目目录和界面中的项目相同吗？不同，一个是 Git 代码组织，另一个是应用里的数据对象。

**易错边界：** 面试时先澄清“项目”指仓库还是工作区项目。

**源码 / 依据：** [backend/app/gateway/routers/projects.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/routers/projects.py)

</details>

### Q025 · L2 · 怎样避免用户重复点击产生重复任务？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 前端禁用重复提交只是第一层；当前后端支持幂等键，按 owner_id、thread_id 和 key 形成作用域，命中已有键时复用已有 run。

**原理与例子：** 网络超时后重试可能遇到“服务端已创建但客户端没收到”的情况。正确复用同一操作的键能避免重复创建；但当前实现没有把输入内容指纹加入冲突校验。

**追问与回答：** 同一个键但输入不同怎么办？当前仍可能复用原 run，客户端必须避免这样复用。改进方案是保存请求指纹，发现内容不一致时明确拒绝；这项检查尚未实现。

**易错边界：** 幂等不等于所有工具副作用天然只执行一次。

**源码 / 依据：** [backend/app/gateway/routers/thread_runs.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/routers/thread_runs.py) · [backend/packages/harness/deerflow/runtime/runs/manager.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/runtime/runs/manager.py)

</details>

### Q026 · L2 · 为什么要维护显式运行状态？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 因为排队、执行、成功、失败和取消具有不同的恢复与界面语义。不能通过“最后一条消息有文字”判断任务成功。

**原理与例子：** 一个任务可能有中间回答但工具失败；也可能后端已完成而网络没有送达最后事件。状态与事件共同提供判断依据。

**追问与回答：** 状态存在哪里？看 runtime/runs 及其存储实现，再看 Gateway 如何更新 thread 的可见状态。

**易错边界：** 不要只靠前端 loading 布尔值表示后台真实状态。

**源码 / 依据：** [backend/packages/harness/deerflow/runtime/runs](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/runtime/runs)

</details>

### Q027 · L2 · 取消任务为什么复杂？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 取消需要停止后续模型与工具调度，同时处理已启动的操作、最终状态和流关闭。协程取消不代表外部进程或远端请求一定立即停止。

**原理与例子：** 例如已发出的 API 请求可能无法撤回，已经写出的文件也需要明确保留或清理策略。取消语义应可预测，并让前端知道是否还有产物。

**追问与回答：** 怎样验证？用可控的慢工具触发取消，检查执行结束、状态、事件和资源回收。

**易错边界：** 不能承诺用户点取消后所有费用立即归零。

**源码 / 依据：** [backend/packages/harness/deerflow/runtime/runs](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/runtime/runs)

</details>

### Q028 · L2 · 重连为什么不能只重新发一次问题？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 重新发送可能创建重复 run。正确做法是先定位原 run，恢复事件或读取持久化状态，再决定是否真的需要新执行。

**原理与例子：** 断线恢复包含两种信息：已经持久化的历史，以及还在发生的新事件。两者合并需要事件顺序与去重规则。

**追问与回答：** 漏了一段事件怎么办？明确报告缺口并重新加载权威状态，不能默默拼接不完整记录。

**易错边界：** 重连是恢复观察，重试是重新执行，不应混用。

**源码 / 依据：** [backend/packages/harness/deerflow/runtime/stream_bridge](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/runtime/stream_bridge)

</details>

### Q029 · L3 · 同一会话并发运行有哪些风险？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 可能同时写 checkpoint、交错工具结果、覆盖元数据，或让前端把两个 run 的事件错误合并。需要定义准入、串行或分支策略。

**原理与例子：** 跨进程场景更不能只用 Python 进程内锁；必须把约束落实到共享持久化层或分布式协调机制。

**追问与回答：** 当前机器怎么处理？当前部署减少并发，但少进程不等于消除了所有异步竞态。

**易错边界：** 降低并发是部署取舍，不是完整分布式一致性证明。

**源码 / 依据：** [backend/app/gateway/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/AGENTS.md)

</details>

### Q030 · L3 · 为什么运行结束事件要和最终状态一致？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 如果先通知完成却没保存最终状态，用户刷新会看到旧结果；如果状态保存了但结束事件丢失，界面可能永远显示运行中。

**原理与例子：** 因此需要规定状态提交、事件发布、流关闭和异常补偿的顺序。故障恢复还要识别孤儿任务，避免无限等待。

**追问与回答：** 能做到绝对原子吗？数据库与事件系统不一定共享事务，需要幂等补偿和状态回查。

**易错边界：** 不能把“用了 Redis”直接等同于端到端恰好一次。

**源码 / 依据：** [backend/app/gateway/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/AGENTS.md)

</details>


## §11 Agent 与模型调用

### Q031 · L1 · Agent 的循环到底是什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 把当前任务和可用工具交给模型，模型选择回答或发出工具调用；框架执行工具，把结果放回上下文，再请求模型。这是有状态的多轮决策，不是模型自己直接运行 Python。

**原理与例子：** 例如“算出销售增幅并生成图”会经历读文件、计算、绘图、检查产物和最终说明。每次调用都有输入、输出和终止条件。

**追问与回答：** 循环什么时候停？模型形成最终回答，或遇到取消、错误、预算和递归限制等条件。

**易错边界：** 不要把一次聊天 API 请求等同于一个完整 Agent 任务。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/lead_agent/agent.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/lead_agent/agent.py)

</details>

### Q032 · L1 · LangGraph 在这里提供什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 它提供图执行、消息状态和 checkpoint 等基础机制。DeerFlow 在这些机制之上组织模型、工具、中间件、子 Agent 和面向用户的运行接口。

**原理与例子：** 可以把 LangGraph 理解为执行骨架，DeerFlow 则决定骨架上装哪些能力以及如何暴露给产品。当前主 Agent 通过 LangChain create_agent 组装，使用 LangGraph 运行机制。

**追问与回答：** 为什么不自己写 while 循环？简单场景可以，但状态恢复、工具消息配对、事件传播和运行控制会迅速增加维护成本。

**易错边界：** 不要说 LangGraph 自动解决所有业务权限和外部副作用。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/lead_agent/agent.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/lead_agent/agent.py)

</details>

### Q033 · L1 · Tool Calling 和直接输出一段命令有什么区别？

<details>
<summary>展开答案与追问</summary>

**口述回答：** Tool Calling 输出结构化工具名、参数和调用标识，框架据此校验并执行。自然语言命令只是文本，除非程序明确解析执行，否则不会自动产生动作。

**原理与例子：** 结构化协议让工具结果能准确对应某次调用，也便于记录耗时和错误。实际安全边界仍在执行端。

**追问与回答：** 参数是 JSON 就可靠吗？不可靠，仍要做类型、范围、权限和资源限制校验。

**易错边界：** 不要把结构正确等同于内容正确或操作安全。

**源码 / 依据：** [backend/packages/harness/deerflow/sandbox/tools.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/sandbox/tools.py)

</details>

### Q034 · L1 · 为什么模型接入需要一个工厂层？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 上层 Agent 应按模型配置使用能力，而不是在各处硬编码供应商请求。工厂负责选择模型实现、参数和能力适配，让调用方式保持集中。

**原理与例子：** 替换模型还要检查工具协议、思考内容、图片输入和 token 统计，并非只换 API 地址。

**追问与回答：** 本项目 DeepSeek 适配是你写的吗？模型适配器属于上游代码，我做的是选用、配置和部署验证。

**易错边界：** 不能把已有适配器归为个人原创。

**源码 / 依据：** [backend/packages/harness/deerflow/models](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/models)

</details>

### Q035 · L2 · 系统提示词怎样影响执行？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 它描述角色、任务执行约束、工具和技能使用原则，引导模型如何规划和汇总。真正权限必须由服务端代码落实，不能只写一句“禁止访问别人的文件”。

**原理与例子：** 提示词适合表达软约束，身份验证、路径校验和资源配额适合做硬约束。二者承担不同职责。

**追问与回答：** 提示词长一点效果就更好吗？不一定，冗余规则会挤占上下文并产生冲突，需要按任务评估。

**易错边界：** 不要把提示词当成安全策略执行器。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/lead_agent/prompt.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/lead_agent/prompt.py)

</details>

### Q036 · L2 · 为什么要用中间件，而不是把逻辑都塞进 Agent？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 中间件把上下文准备、记忆、压缩、工具保护和错误处理放在明确的执行位置。模型循环保持相对稳定，横向能力可以单独配置和测试。

**原理与例子：** 但顺序会改变行为，例如先处理悬空工具消息再发模型请求，避免协议不完整；摘要和持久上下文也需要配合。

**追问与回答：** 有多少层中间件？本版本按配置组装，不能死背固定数字，应指着构造函数解释启用条件和顺序。

**易错边界：** 中间件越多不一定越好，必须考虑副作用和测试成本。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/AGENTS.md)

</details>

### Q037 · L2 · 模型不断重复调用同一个工具怎么办？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先区分任务确实需要重复与无进展循环，再结合相同调用、窗口频率和运行预算进行警告或停止。当前配置启用了 loop_detection。

**原理与例子：** 典型死循环是工具参数一直无效，模型原样重试。应把错误原因清楚返回，必要时缩小任务或请求用户补充信息。

**追问与回答：** 只设置递归上限够吗？它是最后兜底，不能解释重复原因，也不一定及时控制费用。

**易错边界：** 不要把强行终止描述成成功完成。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py)

</details>

### Q038 · L2 · 模型输出被截断和正常结束如何区分？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 需要检查 finish reason、工具参数完整性以及是否产生可用结果。达到输出上限可能留下半个工具调用或未写完的文件说明，不能一律标记成功。

**原理与例子：** 本项目有模型长度与终止响应相关中间件处理异常结束语义。恢复时应保留已经确认的结果，避免盲目从头重做。

**追问与回答：** 把 max_tokens 调很大就解决了吗？不能，它会增加成本，而且还受供应商上限及整个上下文长度限制。

**易错边界：** 文字看起来流畅不代表任务已经完成。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/model_length_finish_reason_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/model_length_finish_reason_middleware.py)

</details>

### Q039 · L3 · 为什么模型返回的工具调用要成对保存？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 模型消息中的 tool_call_id 应能匹配对应的工具结果。删除或压缩其中一半会使后续请求违反工具消息协议，也会使模型误解哪些动作已完成。

**原理与例子：** 失败也应该有明确的错误结果，而不是让工具调用悬空。压缩历史时需保护最近的完整调用链。

**追问与回答：** 怎样测试？构造多工具并行、其中一个失败、取消和摘要裁剪的历史，验证下一轮请求仍合法。

**易错边界：** 不能随意按消息条数裁掉工具结果。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/AGENTS.md)

</details>

### Q040 · L3 · 怎样证明换模型后 Agent 仍能正常工作？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 建立固定任务集，覆盖普通回答、连续工具调用、工具失败、长上下文、图片输入和取消。记录成功率、成本、耗时及失败类型，再比较同一版本配置下的结果。

**原理与例子：** 先用假模型测试编排，再做少量真实 API 验收，可区分框架错误与模型能力差异。当前没有完成跨模型大规模基准。

**追问与回答：** 能用一个“你好”测试替代吗？它只能说明基础接口可用，不能证明 Agent 的执行链可用。

**易错边界：** 不能根据一次成功就宣称模型全面兼容。

**源码 / 依据：** [backend/packages/harness/deerflow/models](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/models) · [backend/tests](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/tests)

</details>


## §12 工具、技能、MCP 与沙箱

### Q041 · L1 · Skill 和 Tool 的区别是什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** Tool 是程序能执行的具体动作；Skill 是围绕任务的一套说明、资源和脚本，告诉 Agent 如何组合动作完成工作。技能本身不等于一个新的大模型。

**原理与例子：** 例如报告技能约定分析步骤和输出格式，实际读取文件、执行计算仍通过工具完成。

**追问与回答：** 技能内容会一次全部进入提示词吗？上游支持发现索引、按需要读取内容，减少不必要的上下文占用。

**易错边界：** 不要把上传一份 SKILL.md 描述成训练模型。

**源码 / 依据：** [backend/packages/harness/deerflow/skills](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/skills) · [skills/public](https://github.com/MHQQysh/rag-project/tree/main/deerflow/skills/public)

</details>

### Q042 · L1 · MCP 在项目里解决什么问题？

<details>
<summary>展开答案与追问</summary>

**口述回答：** MCP 为外部工具与资源提供统一接入协议，减少每个服务都单独写一套模型工具包装的工作。DeerFlow 通过客户端发现和调用配置好的 MCP 工具。

**原理与例子：** 它统一连接方式，但并不自动保证服务可信、权限正确或调用结果准确。

**追问与回答：** Skill 能替代 MCP 吗？Skill 更偏使用说明，MCP 更偏程序接口，两者可以配合。

**易错边界：** 不要把 MCP 当作向量数据库或模型推理框架。

**源码 / 依据：** [backend/packages/harness/deerflow/mcp/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/mcp/AGENTS.md)

</details>

### Q043 · L1 · 为什么需要沙箱？

<details>
<summary>展开答案与追问</summary>

**口述回答：** Agent 会执行模型生成的命令和代码，沙箱提供相对独立的运行环境与文件空间，减少对宿主应用的直接影响。它还让工具环境更可复现。

**原理与例子：** 当前采用 Docker 管理的 AIO 沙箱，模型依旧在外部 API 运行。沙箱负责执行动作，不负责训练大模型。

**追问与回答：** 用了 Docker 就绝对安全吗？不是，还要限制挂载、权限、网络和资源，并及时更新运行环境。

**易错边界：** 容器隔离不是无限权限代码的安全证明。

**源码 / 依据：** [backend/packages/harness/deerflow/community/aio_sandbox](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/community/aio_sandbox)

</details>

### Q044 · L1 · 文件如何从用户手里走到 Agent 手里？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 前端上传到后端，后端校验大小、数量及访问范围，保存到任务相关存储，再通过上下文或工具让 Agent 找到文件。生成的产物也需要通过授权接口返回。

**原理与例子：** “页面出现附件”不等于模型已经读懂内容，解析、图片编码或主动读取还要真正发生。

**追问与回答：** 上传 PDF 会自动变成知识库吗？不会。当前部署关闭自动文档转换，上传与解析、索引、检索是不同环节。

**易错边界：** 不要把上传功能夸大为完整 RAG。

**源码 / 依据：** [backend/app/gateway/upload_ingestion.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/upload_ingestion.py) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q045 · L2 · 新增一个工具怎么做？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先明确输入输出和失败语义，再实现函数并注册到工具配置，按工具组暴露给允许使用的 Agent。写针对参数错误、权限边界和实际结果的测试。

**原理与例子：** 例如知识库检索工具可输入 query 和受控库标识，输出短片段、来源和分数。用户身份应来自服务端上下文。

**追问与回答：** 工具返回越长越好吗？不是，应返回足够证据并把大结果保存成文件供后续读取。

**易错边界：** 不能让客户端直接指定任意服务端路径或任意用户身份。

**源码 / 依据：** [config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/config.example.yaml) · [backend/packages/harness/deerflow/sandbox/tools.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/sandbox/tools.py)

</details>

### Q046 · L2 · 为什么工具大输出需要外置？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 很长的日志或网页会占满模型上下文并增加费用。外置策略保存完整内容，只给模型有限预览与可读取位置。

**原理与例子：** 这样保留可追溯原始结果，又让下一轮决策聚焦关键部分。模型若需细节可按范围继续读取。

**追问与回答：** 预览会漏掉关键信息吗？会，所以预览要明确截断，并保留可靠的后续读取入口。

**易错边界：** 不能把截断内容伪装成完整工具结果。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/AGENTS.md) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q047 · L2 · read-before-write 保护什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 要求 Agent 修改已有内容前先读取相关内容，降低凭想象覆盖文件的风险。它是在工具链里约束执行顺序，而不是仅靠提示词提醒。

**原理与例子：** 读后再写仍可能遇到并发修改，所以高并发场景还应考虑内容哈希、版本号或冲突检测。

**追问与回答：** 对新文件也要先读吗？应按工具策略区分创建与修改，不能机械套用。

**易错边界：** 它不是完整的文件事务或版本控制系统。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/AGENTS.md)

</details>

### Q048 · L2 · 为什么启动沙箱会让小服务器变慢？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 启动容器可能同时加载浏览器、运行时和辅助服务，消耗内存、磁盘读取与 CPU。内存紧张后 swap 会把压力转移到磁盘，延迟明显增加。

**原理与例子：** 本次通过关闭代码编辑器和 Jupyter 网页服务、减少子任务并发、限制容器资源以及延长启动等待来适应小机器。

**追问与回答：** Python 还能运行吗？关闭 Jupyter 网页不等于卸载 Python，命令执行能力仍可用。

**易错边界：** 不能把超时直接归因于模型缺少 GPU。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q049 · L3 · replicas: 1 是否保证最多一个沙箱？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 不能这样保证。在这个实现里它用于暖池容量目标与软上限语义；实际活动容器还受到会话分配和回收路径影响。需要结合实现和监控理解。

**原理与例子：** 同理，子 Agent max_running: 1 只限制相应调度层，不等于网站只能开一个对话，也不等于全站只能有一个 run。

**追问与回答：** 真正全局资源上限怎么做？在容器创建前设置统一准入和配额，并在异常路径释放名额；这是进一步工程设计。

**易错边界：** 不要把某个局部配置夸大成全局并发保证。

**源码 / 依据：** [backend/packages/harness/deerflow/community/aio_sandbox](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/community/aio_sandbox) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q050 · L3 · 沙箱产物如何防止越权下载？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 下载接口必须先确认用户可以访问对应会话，再把请求路径规范化并限制在允许的目录中。单纯隐藏下载链接不能形成保护。

**原理与例子：** 需要考虑 ../、绝对路径、符号链接、归档展开和不同编码等边界；应通过针对性测试确认当前路径的防护。

**追问与回答：** 共享演示账号会怎样？访客拥有同一个身份，因此不能把共享空间内的历史和文件当作彼此私有。

**易错边界：** 按 thread 分目录与按用户授权是两层不同的机制。

**源码 / 依据：** [backend/app/gateway/path_utils.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/path_utils.py) · [backend/app/gateway/conversation_access.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/conversation_access.py)

</details>


## §13 子 Agent、任务分解与并发

### Q051 · L1 · 为什么要把任务交给子 Agent？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 适合把边界明确、相对独立的工作分出去，让主 Agent 聚焦整体目标与最终整合。子 Agent 有独立工作上下文，可以减少主对话被中间细节淹没。

**原理与例子：** 例如分别分析两份资料后返回证据摘要，再由主 Agent 做比较。拆分前应明确输入、交付物和验收标准。

**追问与回答：** 是不是每个问题都要多 Agent？不是，简单任务直接处理更省成本。

**易错边界：** 子 Agent 数量多不代表效果一定好。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/AGENTS.md)

</details>

### Q052 · L1 · 主 Agent 如何发起子任务？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 通过委派工具把具体任务交给执行器，执行器负责建立子 Agent、运行、跟踪状态并返回结果。主 Agent 再结合结果继续决策。

**原理与例子：** 这里的委派是模型选择调用工具，执行权在框架；不是几个聊天窗口自动互相讨论。

**追问与回答：** 子 Agent 是一个新服务器吗？不一定，它首先是独立执行上下文，部署方式由框架决定。

**易错边界：** 不要把逻辑 Agent 数量等同于操作系统进程数量。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/executor.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/executor.py)

</details>

### Q053 · L1 · 怎样判断一个子任务拆得好不好？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 看它是否有独立目标、足够输入、明确产物和可检查标准，同时避免和其他子任务反复共享可变状态。拆分成本应小于节省的工作量。

**原理与例子：** “把报告写好”太宽泛；“从附件 A 提取三项指标并给出页码，返回表格”更易检查。

**追问与回答：** 子任务缺信息怎么办？应回报缺失与假设，而不是静默编造。

**易错边界：** 不能只按字数或文件数量机械拆任务。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/AGENTS.md)

</details>

### Q054 · L1 · 当前部署能同时跑很多子 Agent 吗？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 当前配置 max_running 为 1，max_queued 为 8，采用排队并设置等待超时，目的是控制小机器资源压力。上游框架支持更丰富并发，但这里没有照搬高并发参数。

**原理与例子：** 用户仍可创建多个会话；创建会话、运行任务和子 Agent 调度是不同层次。

**追问与回答：** 为什么不直接调到十个？需要先测模型限流、内存、容器数量和任务成功率。

**易错边界：** 不要把配置能力当作已验证吞吐量。

**源码 / 依据：** [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q055 · L2 · Fan-out/Fan-in 怎么理解？

<details>
<summary>展开答案与追问</summary>

**口述回答：** Fan-out 是把独立工作分发出去，Fan-in 是等待并整合结果。整合阶段要处理成功、失败、缺失和相互矛盾的证据。

**原理与例子：** 当前部署限制执行并发，逻辑上分解了任务也可能排队串行运行，因此不能保证总耗时缩短。

**追问与回答：** 某个子任务失败就整体失败吗？由任务依赖决定，可以重试、降级或明确输出不完整结论。

**易错边界：** 不能把部分结果拼在一起就称作已完成综合分析。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/executor.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/executor.py)

</details>

### Q056 · L2 · 子 Agent 与主 Agent 共享全部聊天记录吗？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 不应假定完整复制。执行器根据委派任务构建子 Agent 的初始状态与上下文，业务身份和工作目录等信息通过受控上下文传递。

**原理与例子：** 隔离上下文能降低噪声，但也可能缺少重要约束，所以委派描述需要自洽。

**追问与回答：** 是否完全隔离文件？上下文隔离不等于独立安全租户，应看沙箱映射和同一会话的共享规则。

**易错边界：** 不能把“独立 Agent”说成“独立用户权限域”。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/executor.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/executor.py)

</details>

### Q057 · L2 · 子任务队列为什么需要等待超时？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 没有超时，任务可能在资源不足时无限等待，用户看不到失败原因，队列也持续积压。等待超时让系统对无法接纳的工作给出明确反馈。

**原理与例子：** 排队时间和执行时间是两类指标，应分别统计。只看模型推理时间会漏掉大量用户感知延迟。

**追问与回答：** 队列越长越好吗？不是，长队列可能只是把立即拒绝变成长时间失败，需要结合服务能力设限。

**易错边界：** 排队成功不等于任务已经开始执行。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/capacity.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/capacity.py) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q058 · L2 · 子任务的进度如何在页面显示？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 后端把开始、步骤和结束等生命周期事件传到前端，前端据此维护任务卡片。必要的历史事件还可以用于刷新后的回查。

**原理与例子：** 事件中必须保留任务关联标识，否则多个任务的文字和工具结果会混在一起。上游使用 task_* 自定义事件承载这类更新。

**追问与回答：** 为什么不直接显示子图所有消息？子图消息如果误当根状态，可能覆盖主对话，必须保持命名空间边界。

**易错边界：** “能看到实时文字”和“状态关联正确”是两件事。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/step_events.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/step_events.py) · [frontend/src/core/tasks](https://github.com/MHQQysh/rag-project/tree/main/deerflow/frontend/src/core/tasks)

</details>

### Q059 · L3 · 为什么 tool_call_id 不能直接当全局子任务 ID？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 供应商的工具调用标识用于关联一次调用及结果，不保证跨父任务全局唯一。执行器还需要服务端生成的 execution_id 管理注册、取消和清理。

**原理与例子：** 把展示关联键和执行所有权键混用，可能让一个 run 取消或读取另一个 run 的子任务。这是并发隔离问题。

**追问与回答：** 前端为什么仍需要 tool_call_id？它要把工具消息、进度卡片和父任务关联起来，标识用途不同。

**易错边界：** 不要认为 UUID 外形相似就意味着相同生命周期。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/AGENTS.md)

</details>

### Q060 · L3 · 多个 Agent 结果冲突时怎么处理？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 不能按人数投票就认定真相，应比较来源可靠性、时效、适用条件和原始证据。主 Agent 应保留不确定性，并在必要时追加针对性核验。

**原理与例子：** 如果两个任务从同一错误网页得到相同结论，它们并不是两份独立证据。评估多 Agent 需要看证据增益而非回答数量。

**追问与回答：** 怎么改进委派协议？要求返回结论、证据位置、假设、未完成项和置信依据；这是可进一步设计的约束。

**易错边界：** 多个模型同意也不等于事实已经验证。

**源码 / 依据：** [backend/packages/harness/deerflow/subagents/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/subagents/AGENTS.md)

</details>


## §14 上下文、记忆与多模态

### Q061 · L1 · Context Engineering 到底在管理什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 管理每次模型调用能看到的信息：目标、历史、工具结果、技能、记忆和工作文件。核心是让必要信息在预算内可用，并且保持来源与权限边界。

**原理与例子：** 它包含写入外部文件、选择相关内容、压缩历史和隔离子任务上下文。不是简单把提示词写长。

**追问与回答：** 为什么长上下文模型仍需要它？上下文长度大不代表所有信息都值得发送，也不代表模型一定注意到关键约束。

**易错边界：** 不能把最大窗口当作每轮必须用满的额度。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/AGENTS.md)

</details>

### Q062 · L1 · 聊天历史、摘要和长期记忆有什么区别？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 历史记录发生过什么；摘要是当前任务历史的压缩表示；长期记忆保存有复用价值的事实或偏好。三者生命周期和准确性要求不同。

**原理与例子：** 一次工具报错可能该保留在运行历史，但不该成为用户长期偏好。摘要也可能丢细节，需要保留原始文件或历史作为证据。

**追问与回答：** 数据库保存了聊天就等于长期记忆吗？不等于，还需要提取、选择、检索、更新和删除机制。

**易错边界：** 持久化与记忆推理不是同一个概念。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/memory/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/memory/AGENTS.md)

</details>

### Q063 · L1 · 当前部署怎样压缩长对话？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 示例配置启用 summarization，token 触发阈值为 32000，保留策略为最近 10 条消息，并限制待摘要内容量。这些是当前部署取舍，不是上游统一默认。

**原理与例子：** 中间件需要协调摘要、保留消息与完整工具调用链，不能理解成简单删除前面的所有消息。

**追问与回答：** 摘要会不会失真？会，因此应保留目标、约束、已完成步骤、关键文件和未解决问题，并可回查原始证据。

**易错边界：** 不能宣称压缩后信息完全无损。

**源码 / 依据：** [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml) · [backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py)

</details>

### Q064 · L1 · 当前记忆检索一定用了向量库吗？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 不是。此部署选用 DeerMem，并配置 fts5 检索适配器，不能把它描述成已经接入某个向量数据库。向量检索只是记忆检索的可选技术路线之一。

**原理与例子：** 关键词检索擅长精确词项，语义检索擅长表达变化，两者需按实际数据评估。

**追问与回答：** RAG 仓库有向量检索就意味着 DeerFlow 也用了？不意味着，两个子项目的运行配置独立。

**易错边界：** 不要把同仓库等同于共享运行时。

**源码 / 依据：** [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml) · [backend/packages/harness/deerflow/agents/memory/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/memory/AGENTS.md)

</details>

### Q065 · L2 · 哪些内容适合进入长期记忆？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 稳定偏好、反复确认的事实和用户明确纠正的信息更有价值。临时工具输出、秘密凭据、未经确认的推断不宜不加区分地保存。

**原理与例子：** 记忆需要来源、时间和可撤销性，过期事实应该更新或淘汰。当前实现有置信度、容量与时效相关配置。

**追问与回答：** 用户说“之前记错了”怎么办？更新或删除旧事实，并防止旧摘要继续覆盖新纠正。

**易错边界：** 模型提取到的事实不自动等于真实事实。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/memory/backends/deermem](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/agents/memory/backends/deermem)

</details>

### Q066 · L2 · 异步写记忆有什么好处和代价？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 它把记忆提取从主回答路径中移开，减少用户等待，但带来最终一致性：刚结束对话时，下一次请求不一定立即看到新记忆。

**原理与例子：** 需要管理队列深度、去抖、失败记录和关闭时的 flush。服务重启也可能影响尚未处理的内容。

**追问与回答：** 如何验证？用可控任务观察入队、处理、持久化和关闭时行为，不能只看返回状态码。

**易错边界：** 不要承诺所有记忆都实时同步。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/memory/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/memory/AGENTS.md) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q067 · L2 · 模型有视觉能力，为什么界面仍可能不能看图？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 需要整条链都支持：前端允许图片、上传成功、后端模型能力声明正确、中间件组装了图片输入，而且真实模型端接受相应格式。任何一环不通都会失败。

**原理与例子：** 当前配置把 Flash 的 supports_vision 标为 true，但这个开关只影响应用行为，不能让一个不支持图片的模型获得视觉能力。

**追问与回答：** 怎样排查？使用一张已知内容的小图，检查实际请求格式、返回错误和识别结果，再逐层定位。

**易错边界：** 不要只凭配置开关宣称视觉端到端已通过验收。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/view_image_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/view_image_middleware.py) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q068 · L2 · Token 预算如何估算？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 每轮输入包括系统提示、技能、历史、工具结果和当前问题，还要给输出留空间。整个任务会多次调用模型，所以总成本是各轮输入输出用量之和。

**原理与例子：** 缓存命中和供应商计费规则可能影响价格；这里只讨论用量，不虚构实时单价。当前 token_usage 开启，token_budget 硬限制未开启。

**追问与回答：** 设置 max_tokens 能限制整个任务成本吗？通常只约束某次生成输出，不能代替整个任务预算。

**易错边界：** 不要把单次输出上限等同于账户消费上限。

**源码 / 依据：** [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml) · [frontend/src/core/threads/token-usage.ts](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/core/threads/token-usage.ts)

</details>

### Q069 · L3 · 如何防止记忆跨用户泄漏？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 身份必须从服务端认证上下文获得，存储和检索都按该身份约束，并检查管理员、内部调用和缺省身份的特殊路径。不能相信请求体自己声明的 user_id。

**原理与例子：** 当前示例 strict_user_scope 为 false，仍需结合实现检查兼容回退；共享演示账号本身也共享同一用户空间，不能夸大为访客隔离。

**追问与回答：** 怎么做验收？用两个真实不同用户分别写入唯一标记，测试正常检索、历史兼容路径与越权请求。

**易错边界：** 仅有目录名不同不足以证明完整隔离。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/memory/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/memory/AGENTS.md) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q070 · L3 · 摘要可能吞掉关键要求，怎么设计验证？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 构造长任务，早期给出可检查约束，中途触发压缩，最后检查约束是否仍满足。还要检查模型请求是否合法、重要文件是否可回读。

**原理与例子：** 例如要求输出两列 CSV 并保持单位，压缩后检查文件列数和单位，比主观判断“回答还不错”更可靠。

**追问与回答：** 评价指标是什么？约束保留率、任务成功率、压缩前后 token 用量及恢复原始证据的能力。

**易错边界：** 这是建议的评估方案，不是本次已经跑完的实验结果。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py) · [backend/tests](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/tests)

</details>


## §15 RAG 原理与同仓库整合

### Q071 · L1 · RAG 和 Agent 是什么关系？

<details>
<summary>展开答案与追问</summary>

**口述回答：** RAG 为回答提供检索证据，Agent 决定如何分步执行任务。RAG 可以是固定流水线，也可以作为 Agent 随时调用的一个工具。

**原理与例子：** 比如 Agent 先查知识库，发现缺少数据后再读附件或计算，最后生成带来源的报告。现在把两个项目放进同一仓库，并不等于这个调用链已经接通。

**追问与回答：** DeerFlow 是纯 RAG 平台吗？不是，它是更通用的任务执行框架。

**易错边界：** 明确区分已实现的独立子项目与未来接口集成。

**源码 / 依据：** [../rag-project/rag_app/service.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/service.py) · [backend/packages/harness/deerflow/agents/lead_agent/agent.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/lead_agent/agent.py)

</details>

### Q072 · L1 · 一条基础 RAG 链路有哪些步骤？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 离线把文档解析、切块、生成向量并存储；在线把问题转成检索表示，召回片段，组织上下文，再调用模型生成答案和来源。

**原理与例子：** 本仓库 rag-project/rag_app/service.py 中的 retrieve 和 chat 可以串起在线主线；解析与切块在相邻模块。

**追问与回答：** 失败可能在哪？解析丢内容、切块破坏语义、召回没命中或生成不忠于证据，要分阶段检查。

**易错边界：** 不要遇到错误就只调提示词。

**源码 / 依据：** [../rag-project/rag_app/service.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/service.py) · [../rag-project/rag_app/parsers.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/parsers.py)

</details>

### Q073 · L1 · 为什么文档需要切块和 overlap？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 整篇文档过长时无法高效检索和放入上下文，切块使召回更聚焦；适度重叠可保留边界附近的连续信息。块过小缺语义，过大引入噪声。

**原理与例子：** 当前 chunking.py 的默认参数以字符长度计，不是 tokenizer token 数。对表格和章节还需检查定位信息是否保留。

**追问与回答：** 如何选大小？在代表性问题集上比较召回率、上下文长度和答案质量，而不是照抄一个数字。

**易错边界：** 重叠会增加存储和重复证据，并非越大越好。

**源码 / 依据：** [../rag-project/rag_app/chunking.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/chunking.py)

</details>

### Q074 · L1 · Embedding 模型和生成模型有什么区别？

<details>
<summary>展开答案与追问</summary>

**口述回答：** Embedding 把文本映射到可比较的向量空间，用于检索；生成模型依据上下文输出文字或工具调用。两者可以来自不同服务。

**原理与例子：** 本仓库 EmbeddingClient 与 LLMClient 分开封装，并有 hash/mock 测试模式。测试模式能验证流程，却不能代表真实语义检索效果。

**追问与回答：** 向量维度不同能混搜吗？不能直接比较，必须使用一致空间或重建索引。

**易错边界：** 不要把 hash 测试向量当作 BGE-M3 的真实效果。

**源码 / 依据：** [../rag-project/rag_app/clients.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/clients.py)

</details>

### Q075 · L2 · 稠密检索、关键词检索和混合检索如何比较？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 稠密检索擅长语义相近但措辞不同的内容；关键词检索擅长专有名词、编号等精确匹配。混合检索组合信号，但需要处理分数尺度与权重。

**原理与例子：** 本仓库 RAG 返回 dense_score、lexical_score、entity_score 等信息，便于追查某条证据为什么被选中。

**追问与回答：** 是不是已经用了标准 BM25？不能仅凭“关键词分数”推断，应看 database.py 的具体计算。

**易错边界：** 不要把所有混合检索都叫成 BM25 加向量库。

**源码 / 依据：** [../rag-project/rag_app/database.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/database.py) · [../rag-project/rag_app/service.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/service.py)

</details>

### Q076 · L2 · Top-k 和阈值如何影响结果？

<details>
<summary>展开答案与追问</summary>

**口述回答：** Top-k 限制返回数量，阈值排除低分候选。过低可能混入噪声，过高可能漏掉证据，合适值需要结合数据和评分方式调节。

**原理与例子：** 服务层还按上下文字符预算截取检索片段，因此“召回了 k 条”不意味着模型最终看到了全部 k 条。

**追问与回答：** 分数能当概率吗？通常不能，除非做过明确校准。

**易错边界：** 不能对不同检索方法沿用同一阈值并假定含义一致。

**源码 / 依据：** [../rag-project/rag_app/service.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/service.py)

</details>

### Q077 · L2 · 答案带引用就一定可信吗？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 不一定。要同时检查引用是否存在、是否指向正确片段、片段是否真正支持该结论，以及是否遗漏冲突证据。编号只是引用形式。

**原理与例子：** 当前 RAG 把来源定位信息传给模型和前端，这是可追溯基础；它不等于已经完成自动事实验证。

**追问与回答：** 没检索到资料怎么办？明确证据不足，按产品策略询问用户或转其他来源，不应伪造引用。

**易错边界：** 有参考文献格式不等于有证据支撑。

**源码 / 依据：** [../rag-project/rag_app/service.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/service.py) · [frontend/src/core/citations/sources.ts](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/core/citations/sources.ts)

</details>

### Q078 · L2 · 自适应 RAG 比固定流程多了什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 它增加路由、文档相关性判断、问题改写和答案检查，根据状态选择下一步。本仓库 rag-project-langgraph 的 graph2 展示了这类条件分支。

**原理与例子：** 这样可能提高复杂问题表现，但也增加模型调用、延迟和错误传播。评估器本身可能误判。

**追问与回答：** 如何避免无限改写？设置明确次数和退出策略，并分别检查每个循环路径。

**易错边界：** 不能因为用了自评模型就宣称消除了幻觉。

**源码 / 依据：** [../rag-project-langgraph/graph2/graph_2.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project-langgraph/graph2/graph_2.py)

</details>

### Q079 · L3 · 怎样真正把现有 RAG 接入 DeerFlow？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 建议先保留 RAG 服务独立部署，提供受身份约束的检索 API，再包装成 DeerFlow 工具或 MCP 工具。返回结构化片段、定位和检索元数据，让主 Agent 负责后续任务。

**原理与例子：** 先做只读检索最容易明确边界；随后再考虑上传、删除、索引更新和统一登录。此项是设计方案，本次仓库整合没有实现这些业务接口连接。

**追问与回答：** 为什么不直接复制所有依赖？两边模型和数据库依赖可能冲突，接口隔离更便于独立升级与回滚。

**易错边界：** 代码放在同一目录树不等于服务已经联通。

**源码 / 依据：** [../rag-project/rag_app/service.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/service.py) · [backend/packages/harness/deerflow/mcp/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/mcp/AGENTS.md)

</details>

### Q080 · L3 · 如何评估 RAG，而不是只看几次回答？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 建立有证据标注的问题集，分开测召回命中、排序质量、回答正确性、证据忠实度、延迟和成本。比较基线与改进时固定文档版本和模型配置。

**原理与例子：** Recall@k 可定义为 top-k 里命中的相关证据数除以标注相关证据总数；无相关证据的问题要单独评价拒答或转路由，不能强行套这个分母。

**追问与回答：** 还要防什么？测试问题泄漏、人工只挑成功案例，以及把 mock 模式当真实结果。

**易错边界：** 这里给的是评估设计，没有编造性能提升百分比。

**源码 / 依据：** [../rag-project/tests](https://github.com/MHQQysh/rag-project/tree/main/rag-project/tests) · [../rag-project-langgraph/graph2/graph_2.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project-langgraph/graph2/graph_2.py)

</details>


## §16 前端、流式响应与交互

### Q081 · L1 · 为什么聊天需要流式返回？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 复杂任务可能执行很久，流式事件让用户及时看到文字、工具动作和阶段变化。它改善可观察性和等待体验，但不必然缩短总计算时间。

**原理与例子：** 用户能区分正在检索、执行代码还是等待模型，出错时也更容易知道发生在哪一步。

**追问与回答：** 首字快是否代表任务快？不代表，要同时看首个有效事件、最终完成时间和成功率。

**易错边界：** 不要把打字动画误当作真实后端流。

**源码 / 依据：** [frontend/src/core/threads/hooks.ts](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/core/threads/hooks.ts) · [backend/app/gateway/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/AGENTS.md)

</details>

### Q082 · L1 · SSE 和 WebSocket 怎么选？

<details>
<summary>展开答案与追问</summary>

**口述回答：** SSE 适合服务器持续向浏览器发送文本事件，普通请求负责发起和控制任务。WebSocket 适合更强双向实时交互，但连接与协议管理更复杂。

**原理与例子：** 聊天结果通常主要是下行流，因此 SSE 是自然选择；停止任务可以走单独请求，不需要为了停止就必须用 WebSocket。

**追问与回答：** SSE 只能用 EventSource 吗？不是，也可以用 fetch 读取流，具体看客户端实现和认证方式。

**易错边界：** HTTP 流不等于只能传普通文字。

**源码 / 依据：** [frontend/src/core/api](https://github.com/MHQQysh/rag-project/tree/main/deerflow/frontend/src/core/api) · [backend/app/gateway/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/AGENTS.md)

</details>

### Q083 · L1 · 前端为什么分 components 和 core？

<details>
<summary>展开答案与追问</summary>

**口述回答：** components 聚焦界面和交互呈现，core 集中接口、类型、状态处理与业务 hooks。分层让一个接口变更不必在许多页面里重复修复。

**原理与例子：** 比如认证逻辑集中在 core/auth，而演示按钮在 components/auth 使用该体系。

**追问与回答：** 所有状态都放全局好吗？不是，输入框临时状态适合局部，跨页面会话或服务端资源才考虑共享。

**易错边界：** 目录分层要看依赖是否清晰，不只是文件夹名字。

**源码 / 依据：** [frontend/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/AGENTS.md) · [frontend/src/core](https://github.com/MHQQysh/rag-project/tree/main/deerflow/frontend/src/core)

</details>

### Q084 · L1 · 新建多个对话靠什么实现？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 每个会话有独立 thread 标识，列表负责展示与切换，消息和运行状态按对应标识获取。一次运行不会自动等于创建一个新会话。

**原理与例子：** 演示登录后进入新对话页，访客可发起对话；但当前所有演示访客共用一个账号，所以历史不是访客私有的。

**追问与回答：** 浏览器关掉就删除会话吗？不应这样假定，持久化生命周期由后端和删除逻辑决定。

**易错边界：** 不要把浏览器标签页和后端会话混为一谈。

**源码 / 依据：** [frontend/src/core/threads](https://github.com/MHQQysh/rag-project/tree/main/deerflow/frontend/src/core/threads) · [frontend/src/components/auth/demo-login.tsx](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/components/auth/demo-login.tsx)

</details>

### Q085 · L2 · 为什么 Nginx 会让流式输出看起来一次性返回？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 代理缓冲可能积攒后端事件，直到达到阈值才发给浏览器。需要针对流式接口检查缓冲、超时和压缩设置，以及后端是否及时 flush。

**原理与例子：** 还可能是客户端渲染合并，不应只改服务器就认定解决。用时间戳逐层比较事件产生、到达与显示时间。

**追问与回答：** 所有路由都关闭缓存好吗？不必，静态资源和事件流有不同需求。

**易错边界：** 不要为了 SSE 随意禁用整个站点的所有优化。

**源码 / 依据：** [deploy/ecs/nginx.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/nginx.conf) · [docker/nginx](https://github.com/MHQQysh/rag-project/tree/main/deerflow/docker/nginx)

</details>

### Q086 · L2 · 为什么消息不能按到达顺序直接追加？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 网络重连、历史加载和实时事件可能交错，某条消息还可能分多次更新。需要稳定标识、排序和合并规则，避免重复与顺序错乱。

**原理与例子：** 工具消息还要和对应调用关联；子任务事件不应直接覆盖主对话状态。

**追问与回答：** 刷新之后出现两份回答怎么查？比较消息 ID、历史载入和流式合并路径，检查是否重放了同一事件。

**易错边界：** 数组 append 不等于可靠消息模型。

**源码 / 依据：** [frontend/src/core/threads/message-order.ts](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/core/threads/message-order.ts) · [frontend/src/core/threads/stream-state.ts](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/core/threads/stream-state.ts)

</details>

### Q087 · L2 · 模型生成的 Markdown 如何安全显示？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 把它当不可信内容，谨慎处理 HTML、链接、嵌入资源和代码块。显示一段脚本与执行脚本必须有清晰边界。

**原理与例子：** 图表或产物预览涉及更复杂内容时，还要检查隔离和来源策略。界面美观不能代替渲染安全。

**追问与回答：** 用户上传的文件名呢？也需要正确编码和渲染，不能拼进 HTML 当模板执行。

**易错边界：** 不能因为内容来自模型就信任其中的链接或脚本。

**源码 / 依据：** [frontend/src/core/streamdown](https://github.com/MHQQysh/rag-project/tree/main/deerflow/frontend/src/core/streamdown) · [frontend/src/core/artifacts](https://github.com/MHQQysh/rag-project/tree/main/deerflow/frontend/src/core/artifacts)

</details>

### Q088 · L2 · 演示按钮为什么登录后整页跳转？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 服务端设置会话 cookie 后，完整导航到聊天页，让认证状态在新页面初始化时重新获取。这样减少旧页面 AuthProvider 仍持有未登录状态的竞态。

**原理与例子：** 按钮还处理正在登录、失败和开关关闭等状态，避免重复点击和空白页面。

**追问与回答：** 为什么不用把密码填在输入框里？浏览器可见的密码会被访客拿走，也会混淆管理员与演示权限。

**易错边界：** 这里使用服务端签发普通演示会话，不是前端硬编码密码。

**源码 / 依据：** [frontend/src/components/auth/demo-login.tsx](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/components/auth/demo-login.tsx)

</details>

### Q089 · L3 · 断网后界面应该怎样恢复？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先告诉用户连接中断，再查询原任务状态并恢复可用历史。只有确认需要重新执行时才创建新 run，避免重复工具副作用。

**原理与例子：** 对还在运行的任务恢复观察，对已经结束的任务加载最终产物，对无法恢复的事件缺口明确提示。

**追问与回答：** 页面 loading 是否可以自己超时归零？可以结束等待显示，但不能因此把后端任务改判成功或取消。

**易错边界：** 前端观察状态与服务端执行状态需要区分。

**源码 / 依据：** [frontend/src/core/threads/stream-state.ts](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/core/threads/stream-state.ts) · [backend/packages/harness/deerflow/runtime/stream_bridge](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/runtime/stream_bridge)

</details>

### Q090 · L3 · 前端测试如何覆盖演示登录？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 用受控接口响应验证：开关开启出现按钮、点击发起正确请求、成功跳转、失败显示错误，以及关闭时不出现入口。再用服务端测试确认真实权限。

**原理与例子：** UI 测试保证按钮流程，不能替代 JWT、cookie 和管理员权限测试。本次已有三项按钮交互测试及后端相关回归记录。

**追问与回答：** 是不是浏览器线上全链路也通过了？不能这样说；公网接入仍有备案拦截问题，功能测试与公网可达性分开记录。

**易错边界：** 不要把组件 mock 测试描述成真实公网用户验收。

**源码 / 依据：** [frontend/tests](https://github.com/MHQQysh/rag-project/tree/main/deerflow/frontend/tests) · [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md)

</details>


## §17 持久化、可靠性与测试

### Q091 · L1 · 数据库、文件和 Redis 分别保存什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 数据库保存用户、会话、运行等结构化状态；文件存放上传资料、产物和部分配置；Redis 在当前部署中用于流桥接。具体真相来源要按数据类型区分。

**原理与例子：** 不能只备份源码就期待恢复聊天，也不能认为 Redis 有数据就代表所有运行状态都安全持久化。

**追问与回答：** 当前用哪个数据库？ECS 配置是 SQLite，运行事件配置为数据库后端。

**易错边界：** 仓库里的数据库接口支持范围与当前启用后端不同。

**源码 / 依据：** [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml) · [backend/packages/harness/deerflow/persistence](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/persistence)

</details>

### Q092 · L1 · Checkpoint 和聊天记录有什么不同？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 聊天记录面向用户阅读，checkpoint 保存图运行所需的状态，用于后续执行或状态恢复。两者可能有关联，但不是同一个数据结构。

**原理与例子：** 只存最终回答通常不足以恢复工具调用、摘要和运行上下文。外部文件与副作用也不自动包含在 checkpoint 内。

**追问与回答：** 有 checkpoint 就能任意续跑吗？不能，仍需看节点恢复语义、版本兼容和外部操作是否可重放。

**易错边界：** 不要把图状态快照说成整台机器快照。

**源码 / 依据：** [backend/packages/harness/deerflow/runtime/checkpointer](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/runtime/checkpointer) · [backend/packages/harness/deerflow/agents/thread_state.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/thread_state.py)

</details>

### Q093 · L1 · 为什么小部署可以先用 SQLite？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 它部署简单、不需要独立数据库服务，适合单机和相对有限的写并发。当前资源紧张，减少常驻服务有实际价值。

**原理与例子：** 当多进程写入、复杂事务或横向扩容成为瓶颈时，应评估 Postgres，而不是把 SQLite 的简单性当成无限扩展能力。

**追问与回答：** 有没有迁移层？本项目有统一持久化代码与迁移目录，升级要关注 schema 兼容。

**易错边界：** 不能仅按用户数量断言哪个数据库一定够用。

**源码 / 依据：** [backend/packages/harness/deerflow/persistence/engine.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/persistence/engine.py) · [backend/packages/harness/deerflow/persistence/migrations](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/persistence/migrations)

</details>

### Q094 · L1 · 健康检查能证明聊天可用吗？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 基础健康检查只能说明进程或依赖达到它所检查的条件。完整聊天还涉及认证、模型、工具、沙箱和流式返回，需要单独端到端验收。

**原理与例子：** 建议从存活检查、就绪检查到一条可控任务逐步扩大范围，失败时更容易定位。

**追问与回答：** 本次实际验证了什么？部署记录包含登录相关接口与生成 result.txt、内容 323 的沙箱任务验收。

**易错边界：** 一个 health 返回 200 不等于所有能力正常。

**源码 / 依据：** [backend/app/gateway/health.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/health.py) · [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md)

</details>

### Q095 · L2 · 哪些错误可以自动重试？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 临时网络失败、可恢复限流等可以在预算内重试；参数错误、权限拒绝通常需要修正原因。具有副作用的工具还要先确认操作是否已发生。

**原理与例子：** 策略应包含退避、次数上限和总时间预算，并遵守供应商的重试提示。

**追问与回答：** 写文件超时可以直接再写吗？要检查是否已写入、是否幂等，必要时使用操作标识或内容校验。

**易错边界：** 不能对所有异常统一无限重试。

**源码 / 依据：** [backend/packages/harness/deerflow/models](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/models) · [backend/packages/harness/deerflow/sandbox/tools.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/sandbox/tools.py)

</details>

### Q096 · L2 · async 函数里为什么仍可能卡住整个服务？

<details>
<summary>展开答案与追问</summary>

**口述回答：** async 只是协作调度形式，如果其中直接运行阻塞文件操作、同步网络调用或重计算，仍会阻塞事件循环。需要异步库或合适的线程、进程边界。

**原理与例子：** 当前项目有阻塞 I/O 测试来识别这类路径。把同步调用改成函数名带 async 不会自动使它非阻塞。

**追问与回答：** 线程池能解决所有问题吗？不能，线程池会饱和，CPU 密集任务还需另行评估。

**易错边界：** 并发连接多不等于服务具有高吞吐。

**源码 / 依据：** [backend/tests/blocking_io](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/tests/blocking_io) · [backend/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/AGENTS.md)

</details>

### Q097 · L2 · 如何设计能定位问题的日志？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 按 request、thread、run 和子任务关联记录阶段、耗时、错误类型与必要配置版本。日志应足够还原流程，同时避免保存密钥和不必要的用户原文。

**原理与例子：** 例如“模型请求失败”应能区分超时、限流和参数错误，而不是只打印一句 error。

**追问与回答：** trace 放在哪层？当前上游要求在图调用根部挂 tracing，避免同时在子层重复创建相同 span。

**易错边界：** 不能把带全部请求头的日志公开到 GitHub。

**源码 / 依据：** [backend/app/gateway/trace_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/trace_middleware.py) · [backend/packages/harness/deerflow/agents/lead_agent/agent.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/lead_agent/agent.py)

</details>

### Q098 · L2 · 这个项目的测试应该分哪几层？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 单元测试验证纯逻辑和边界；接口测试验证认证、状态和协议；组件测试验证界面交互；端到端验证真实模型与沙箱协作。各层解决不同的不确定性。

**原理与例子：** 外部 API 验收慢且花费额度，应保留少量代表性任务，日常回归尽量依赖确定性测试。

**追问与回答：** 本次全量后端测试通过了吗？没有完整跑完。相关功能集通过，基线全量运行中止时的通过数量不能冒充全量结果。

**易错边界：** 报告测试范围和未验证部分，比只报一个大数字更可信。

**源码 / 依据：** [backend/tests](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/tests) · [frontend/tests](https://github.com/MHQQysh/rag-project/tree/main/deerflow/frontend/tests) · [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md)

</details>

### Q099 · L3 · 任务执行到一半服务器重启怎么恢复？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先从持久化运行记录识别未结束任务，再结合 ownership、lease 和 checkpoint 判断能恢复、需终止还是等待原执行者。对已经发生的工具副作用要单独核查。

**原理与例子：** 多实例恢复更需要租约和 fencing，避免两个执行者同时接管。当前部署没有启用所有多实例恢复选项。

**追问与回答：** 可以开两个 Gateway 就高可用了吗？不行，数据库、流桥接、共享文件、任务所有权和限额都要一起设计。

**易错边界：** 不能把进程自动重启说成任务必然自动续跑。

**源码 / 依据：** [backend/packages/harness/deerflow/runtime/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/runtime/AGENTS.md) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q100 · L3 · 如何做可靠的备份与回滚？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 分别备份源码版本、配置、数据库和用户文件；对 SQLite 使用一致性备份方式，避免随意复制正在变化的文件集合。升级前确认迁移是否允许回退。

**原理与例子：** 发布失败可以回滚应用包，但新 schema 和新数据未必兼容旧程序。需要演练恢复，不能只确认备份文件存在。

**追问与回答：** 密钥也放仓库备份吗？不，应放受控的秘密管理与备份渠道，源码仓库只保留示例。

**易错边界：** 没有恢复演练的备份只能算尚未验证。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [backend/packages/harness/deerflow/persistence/migrations/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/persistence/migrations/AGENTS.md)

</details>


## §18 部署、资源、域名与 GitHub

### Q101 · L1 · 为什么完整 DeerFlow 不能只放 GitHub Pages？

<details>
<summary>展开答案与追问</summary>

**口述回答：** Pages 发布静态文件，完整 DeerFlow 还需要运行 Python Gateway、动态前端、模型调用和沙箱等服务。因此代码可以放 GitHub，应用运行在服务器。

**原理与例子：** 本次 Pages 发布的是项目导航和题解阅读页，原版应用仍在 ECS。浏览器轻量版与完整 DeerFlow 保持不同目录和说明。

**追问与回答：** Pages 能接外部后端吗？可以设计这种架构，但还要处理认证、跨域和动态前端要求，不是上传源码后自动成立。

**易错边界：** 不要把代码托管、静态托管和后端部署当成一件事。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [../scripts/assemble-pages.mjs](https://github.com/MHQQysh/rag-project/blob/main/scripts/assemble-pages.mjs)

</details>

### Q102 · L1 · 用了 DeepSeek API 为什么不需要本机 GPU？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 模型推理在供应商服务端执行，本机负责网页、任务编排、文件和工具运行。CPU、内存和磁盘仍然重要，但不需要为了调用 API 下载整个模型。

**原理与例子：** 如果另外部署本地 embedding 或大模型，就要单独评估它们的资源需求，不能套用当前 API 部署结论。

**追问与回答：** 那服务器为什么还会卡？可能是沙箱冷启动、磁盘 I/O、内存压力或并发造成的。

**易错边界：** 不要把所有延迟都归因于 GPU。

**源码 / 依据：** [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q103 · L1 · 当前低内存服务器的主要取舍是什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 优先保持完整应用的主要链路，降低执行并发，使用生产构建，并把前端构建移到资源更充足的 Linux/WSL 机器。运行时保留必要服务和持久化。

**原理与例子：** 这些取舍适合个人低并发展示，没有证明它能承载大量公网用户。swap 能缓解内存不足，但磁盘换页会拉长响应时间。

**追问与回答：** 能给出最大在线人数吗？需要压测，而且“在线浏览”和“同时运行 Agent”消耗完全不同。

**易错边界：** 不能只凭机器规格编造承载量，应测量真实任务的内存、延迟和成功率。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md)

</details>

### Q104 · L1 · IP、域名和端口分别是什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** IP 指向服务器网络地址，域名通过 DNS 解析到目标，端口区分机器上的服务。浏览器访问 HTTPS 域名通常连接 443，再由 Nginx 路由到内部服务。

**原理与例子：** 给 deerflow 子域名加 A 记录，只改变该子域名；保留原来根域和 www 记录，原网站就不会因这条新增记录被替换。

**追问与回答：** 为什么解析对了还打不开？还要检查安全组、监听服务、TLS、代理与云平台接入状态。

**易错边界：** DNS 成功不等于应用可用。

**源码 / 依据：** [deploy/ecs/public-entry.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/public-entry.conf) · [deploy/ecs/nginx.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/nginx.conf)

</details>

### Q105 · L2 · HTTPS、登录和权限控制各解决什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** HTTPS 保护传输并验证站点身份；登录识别用户；权限控制决定用户能访问哪些资源和动作。三者缺一时，其他机制不能自动补上。

**原理与例子：** 证书正常但后端鉴权错误仍可能越权；登录正常但 HTTP 传输也不符合公开服务预期。

**追问与回答：** 为什么内部端口不直接公开？统一入口更便于 TLS、路由和暴露面管理。

**易错边界：** 不能说“有小锁所以系统安全”。

**源码 / 依据：** [deploy/ecs/public-entry.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/public-entry.conf) · [backend/app/gateway/auth_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/auth_middleware.py)

</details>

### Q106 · L2 · 404、502、403 分别怎么排查？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 404 先确认请求是否到正确虚拟主机和路由；502 检查代理上游进程、地址和超时；403 检查应用权限、代理策略或云平台拦截。状态码只是线索。

**原理与例子：** 本次曾观察到 Nginx 404 和阿里云 Beaver 的备案拦截，应看响应内容和服务标识，不要把不同层错误混成同一问题。

**追问与回答：** 服务器里能打开就代表外网能用吗？不代表，内外访问可能经过不同链路。

**易错边界：** 不要在没定位时反复改前端代码碰运气。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [deploy/ecs/public-entry.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/public-entry.conf)

</details>

### Q107 · L2 · 为什么生产环境不用开发服务器？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 开发模式包含热更新、额外监听和调试开销，行为也与生产构建不同。生产部署应使用已构建资源与明确的服务管理方式。

**原理与例子：** 本次前端打包 standalone，并由 systemd 管理前后端。服务管理能负责启动、重启和日志，但不代替数据备份。

**追问与回答：** 源码改完会立即生效吗？前端需要重新构建部署，后端通常需要重启，代理修改要校验再 reload。

**易错边界：** Git push 不等于服务器自动更新。

**源码 / 依据：** [deploy/ecs/build-frontend-wsl.sh](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/build-frontend-wsl.sh) · [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md)

</details>

### Q108 · L2 · 导入完整源码后，上游 CI 会自动在主仓库运行吗？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 不会。GitHub Actions 发现的是仓库根 .github/workflows 下的工作流；导入到 deerflow/.github/workflows 的上游文件只是源码的一部分，不会自动执行。

**原理与例子：** 若要启用上游测试，需要在主仓库工作流中适配 working-directory、依赖缓存和路径触发规则。本次根工作流只增加了面试文档发布，不能因此声称整个 DeerFlow CI 已启用。

**追问与回答：** 保留嵌套工作流有什么用？可以作为上游行为参考与后续迁移基础；正式启用前还应检查权限、secrets 与运行成本。

**易错边界：** 仓库里存在工作流文件，不代表平台已经识别并执行它。

**源码 / 依据：** [docs/UPSTREAM.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/docs/UPSTREAM.md) · [../.github/workflows/commerce-pages.yml](https://github.com/MHQQysh/rag-project/blob/main/.github/workflows/commerce-pages.yml)

</details>

### Q109 · L3 · 以后怎么同步上游又保留自己的改动？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 记录导入基线和个人补丁范围，更新时比较新旧上游，再把个人改动重新应用并回归验证。本次是源码快照导入，不包含上游完整提交历史。

**原理与例子：** 长期维护可用专门同步分支或 subtree 等策略，但必须先明确许可证、冲突解决和部署验证流程。

**追问与回答：** 直接覆盖整个目录好吗？可能丢失演示入口、部署配置和文档，应先审查差异。

**易错边界：** 不能把一次源码复制说成已经建立自动上游同步。

**源码 / 依据：** [README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/README.md) · [docs/UPSTREAM.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/docs/UPSTREAM.md)

</details>

### Q110 · L3 · 怎样设计从 GitHub 到 ECS 的自动部署？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 建议让流水线先测试、构建和打包，产生可识别版本，再通过受控部署凭据发布、健康检查并保留回滚包。运行数据库和真实配置不应被构建包覆盖。

**原理与例子：** 前端构建与服务器运行环境要兼容，发布时还要考虑正在运行的 Agent 任务。当前只有 Pages 自动发布，ECS 应用尚未配置自动部署。

**追问与回答：** 需要把 SSH 私钥写进代码吗？不，应使用受保护的 CI secrets 或更合适的短期凭据。

**易错边界：** 这是一项后续设计，不是本次已经交付的 CI/CD 能力。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [../.github/workflows/commerce-pages.yml](https://github.com/MHQQysh/rag-project/blob/main/.github/workflows/commerce-pages.yml)

</details>


## §19 演示登录、安全与面试压轴

### Q111 · L1 · “进入演示”按钮到底做了什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 前端先查询演示开关，点击后向服务端申请演示会话。后端验证预先创建的普通演示用户，签发正常认证 cookie，再进入聊天页。

**原理与例子：** 账号由服务器预先配置，无密码且非管理员；浏览器没有拿到管理员密码。访客无需注册，但仍经过受控认证入口。

**追问与回答：** 按钮隐藏了就关闭演示了吗？不够，必须关闭服务端开关；当前请求校验也会拒绝被关闭的演示身份。

**易错边界：** UI 隐藏不是后端权限控制。

**源码 / 依据：** [backend/app/gateway/auth/demo.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/auth/demo.py) · [backend/app/gateway/routers/auth.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/routers/auth.py)

</details>

### Q112 · L1 · 为什么不把自己的账号密码默认填好？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 默认填充到公开网页就等于把凭据交给访客，访客可能获得管理员能力并长期复用。独立普通演示用户把展示与个人管理身份分开。

**原理与例子：** 当前还限制演示用户修改身份相关操作或创建长期访问凭据。管理员仍通过原登录方式进入。

**追问与回答：** 演示用户和管理员会话相同吗？认证机制复用，但用户身份和权限不同。

**易错边界：** 不能给访客使用管理员 JWT。

**源码 / 依据：** [backend/app/gateway/auth/demo.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/auth/demo.py) · [frontend/src/components/auth/demo-login.tsx](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/components/auth/demo-login.tsx)

</details>

### Q113 · L1 · 现在的演示模式有哪些明确限制？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 所有访客使用同一个演示身份，因此对话和文件属于共享空间；请求消耗服务器配置的模型额度。它适合公开样例或受控展示，不能当成访客私密工作区。

**原理与例子：** 当前尚未增加独立访客身份、专门的匿名额度系统和每人独立沙箱配额。公开规模扩大前要补这些设计。

**追问与回答：** 能上传私人材料吗？页面已提示共享属性，不应这样使用。

**易错边界：** 普通用户不等于只读用户，仍要评估它可调用的工具。

**源码 / 依据：** [frontend/src/components/auth/demo-login.tsx](https://github.com/MHQQysh/rag-project/blob/main/deerflow/frontend/src/components/auth/demo-login.tsx) · [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md)

</details>

### Q114 · L1 · 如何安排一次十分钟的现场项目演示？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先用一张图讲清请求链路，再进入演示账号创建对话，提交一个可检查的工具任务，最后打开产物和对应源码。为冷启动等待预留时间，并准备已有的验收记录。

**原理与例子：** 任务可选“用 Python 计算 17×19，生成 result.txt”，验收点是实际工具执行和文件内容 323，而不是回答口头声称已完成。演示时说明普通访客空间共享，避免上传私人材料。

**追问与回答：** 如果现场公网被拦截呢？明确说明接入问题，展示已记录的接口与文件验收，或在事先验证的本地环境演示；不能把录屏伪装成实时运行。

**易错边界：** 先独立演练整个流程，能够解释每一步；一次展示不能代表高并发稳定性或全部工具可用。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md)

</details>

### Q115 · L2 · JWT 存在 cookie 里还需要检查什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 需要检查签名、有效期、用户是否仍有效、token 版本及 cookie 属性。浏览器自动带 cookie 时还需处理 CSRF 和来源约束。

**原理与例子：** 登录只是签发凭据，后续每次受保护请求还要校验身份与权限；关闭演示入口也要影响已有演示会话。

**追问与回答：** JWT 能立即撤销吗？纯无状态签名验证不容易，当前体系结合用户状态与 token 版本等服务端检查。

**易错边界：** 不要把解析出 JWT 内容等同于验证签名成功。

**源码 / 依据：** [backend/app/gateway/auth/jwt.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/auth/jwt.py) · [backend/app/gateway/auth_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/auth_middleware.py)

</details>

### Q116 · L2 · 演示登录为什么还要考虑 CSRF？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 浏览器会自动携带某些 cookie，跨站页面可能诱导用户发起请求。首次登录不能依赖尚未建立的 CSRF cookie，但可以在相应豁免路径上保持来源检查等约束。

**原理与例子：** 本次在现有 CSRF 中间件里增加明确的演示登录路径，而不是全站关闭保护。登录后继续使用原认证与请求机制。

**追问与回答：** CORS 能完全替代 CSRF 吗？不能，是否能发出请求与是否能读取响应是不同问题。

**易错边界：** 豁免一个初次认证端点不等于豁免全部修改操作。

**源码 / 依据：** [backend/app/gateway/csrf_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/csrf_middleware.py) · [backend/app/gateway/routers/auth.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/routers/auth.py)

</details>

### Q117 · L2 · 网页或文档里的恶意指令如何影响 Agent？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 模型可能把外部内容中的“忽略规则、读取秘密”等文字误当指令，这就是提示注入风险。外部资料应视为数据，工具执行还要受权限和资源边界约束。

**原理与例子：** 需要把可信指令与不可信内容分开，避免把秘密暴露给不必要的工具，并对敏感动作实行服务端限制。

**追问与回答：** 只加一句“忽略恶意指令”够吗？不够，模型判断不是可靠的强制访问控制。

**易错边界：** RAG 检索命中并不让那段内容自动获得指令权限。

**源码 / 依据：** [backend/packages/harness/deerflow/agents/middlewares/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/packages/harness/deerflow/agents/middlewares/AGENTS.md) · [backend/packages/harness/deerflow/authz](https://github.com/MHQQysh/rag-project/tree/main/deerflow/backend/packages/harness/deerflow/authz)

</details>

### Q118 · L2 · 如何防止公开演示把模型额度用光？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 后续应在请求准入处加入用户或访客配额、IP 辅助限流、全局并发与预算保护，并控制高成本工具和上传规模。仅限制子 Agent 并发不能覆盖所有费用来源。

**原理与例子：** 当前配置有模型并发限制和用量记录，但 token_budget 硬限制关闭，也没有本次新增的按访客计费系统。

**追问与回答：** IP 限流够吗？不够，共享网络会误伤，分布式来源也能绕过，需要组合身份与全局预算。

**易错边界：** 这些是待实施措施，不能写成已交付防滥用平台。

**源码 / 依据：** [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml) · [backend/app/gateway/auth/demo.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/auth/demo.py)

</details>

### Q119 · L3 · 如果面试官要求现场定位“能登录但发不出消息”，怎么回答？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先复现并观察失败请求，再按身份授权、run 创建、事件流、模型调用和工具启动分层检查。拿到具体错误、关联 ID 和时间线后再改代码。

**原理与例子：** 若没有创建 run，先查请求与权限；若 run 已开始但无输出，查流桥接和模型；若在工具阶段停住，查沙箱与资源。

**追问与回答：** 先重启服务器行不行？重启可能临时恢复，却可能丢失诊断线索，应先保存必要状态再采取恢复措施。

**易错边界：** 不要在不知道失败层次时一次改很多配置。

**源码 / 依据：** [backend/app/gateway/AGENTS.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/AGENTS.md) · [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md)

</details>

### Q120 · L3 · 如果再给你两周，你最值得改进什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 先建立可重复的端到端任务集和公网可达性验收，再为演示补独立访客身份、额度与隔离；随后把现有 RAG 以只读检索工具接入。按风险和可验证价值排序。

**原理与例子：** 每项都应给出验收条件：不同访客不能读取对方数据、预算超限明确拒绝、检索结果能追溯到文档、回归任务稳定通过。

**追问与回答：** 为什么不优先加更多 Agent？基础可靠性、权限和证据链还没验证好时，加复杂度会放大问题。

**易错边界：** 这是个人改进计划，不能列为已经实现的履历成果。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [../rag-project/rag_app/service.py](https://github.com/MHQQysh/rag-project/blob/main/rag-project/rag_app/service.py)

</details>
