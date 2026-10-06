# 第 04 章 · Agent 与模型调用

[返回学习入口](README.md)

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
