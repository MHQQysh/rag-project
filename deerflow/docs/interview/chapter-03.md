# 第 03 章 · 请求、会话与运行状态

[返回学习入口](README.md)

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
