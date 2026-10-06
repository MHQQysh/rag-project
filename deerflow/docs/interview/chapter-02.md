# 第 02 章 · 总体架构与代码导航

[返回学习入口](README.md)

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
