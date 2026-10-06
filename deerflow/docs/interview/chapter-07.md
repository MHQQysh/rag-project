# 第 07 章 · 上下文、记忆与多模态

[返回学习入口](README.md)

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
