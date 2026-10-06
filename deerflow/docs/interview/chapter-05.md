# 第 05 章 · 工具、技能、MCP 与沙箱

[返回学习入口](README.md)

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
