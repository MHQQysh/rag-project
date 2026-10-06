# 第 10 章 · 持久化、可靠性与测试

[返回学习入口](README.md)

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
