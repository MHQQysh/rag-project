# 第 09 章 · 前端、流式响应与交互

[返回学习入口](README.md)

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
