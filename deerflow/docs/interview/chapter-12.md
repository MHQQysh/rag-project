# 第 12 章 · 演示登录、安全与面试压轴

[返回学习入口](README.md)

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
