# 第 06 章 · 子 Agent、任务分解与并发

[返回学习入口](README.md)

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
