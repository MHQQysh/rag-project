# 第 08 章 · RAG 原理与同仓库整合

[返回学习入口](README.md)

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
