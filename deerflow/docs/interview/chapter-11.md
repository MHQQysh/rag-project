# 第 11 章 · 部署、资源、域名与 GitHub

[返回学习入口](README.md)

### Q101 · L1 · 为什么完整 DeerFlow 不能只放 GitHub Pages？

<details>
<summary>展开答案与追问</summary>

**口述回答：** Pages 发布静态文件，完整 DeerFlow 还需要运行 Python Gateway、动态前端、模型调用和沙箱等服务。因此代码可以放 GitHub，应用运行在服务器。

**原理与例子：** 本次 Pages 发布的是项目导航和题解阅读页，原版应用仍在 ECS。浏览器轻量版与完整 DeerFlow 保持不同目录和说明。

**追问与回答：** Pages 能接外部后端吗？可以设计这种架构，但还要处理认证、跨域和动态前端要求，不是上传源码后自动成立。

**易错边界：** 不要把代码托管、静态托管和后端部署当成一件事。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [../scripts/assemble-pages.mjs](https://github.com/MHQQysh/rag-project/blob/main/scripts/assemble-pages.mjs)

</details>

### Q102 · L1 · 用了 DeepSeek API 为什么不需要本机 GPU？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 模型推理在供应商服务端执行，本机负责网页、任务编排、文件和工具运行。CPU、内存和磁盘仍然重要，但不需要为了调用 API 下载整个模型。

**原理与例子：** 如果另外部署本地 embedding 或大模型，就要单独评估它们的资源需求，不能套用当前 API 部署结论。

**追问与回答：** 那服务器为什么还会卡？可能是沙箱冷启动、磁盘 I/O、内存压力或并发造成的。

**易错边界：** 不要把所有延迟都归因于 GPU。

**源码 / 依据：** [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md) · [deploy/ecs/config.example.yaml](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/config.example.yaml)

</details>

### Q103 · L1 · 当前低内存服务器的主要取舍是什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 优先保持完整应用的主要链路，降低执行并发，使用生产构建，并把前端构建移到资源更充足的 Linux/WSL 机器。运行时保留必要服务和持久化。

**原理与例子：** 这些取舍适合个人低并发展示，没有证明它能承载大量公网用户。swap 能缓解内存不足，但磁盘换页会拉长响应时间。

**追问与回答：** 能给出最大在线人数吗？需要压测，而且“在线浏览”和“同时运行 Agent”消耗完全不同。

**易错边界：** 不能只凭机器规格编造承载量，应测量真实任务的内存、延迟和成功率。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [deploy/ecs/部署说明.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E.md)

</details>

### Q104 · L1 · IP、域名和端口分别是什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** IP 指向服务器网络地址，域名通过 DNS 解析到目标，端口区分机器上的服务。浏览器访问 HTTPS 域名通常连接 443，再由 Nginx 路由到内部服务。

**原理与例子：** 给 deerflow 子域名加 A 记录，只改变该子域名；保留原来根域和 www 记录，原网站就不会因这条新增记录被替换。

**追问与回答：** 为什么解析对了还打不开？还要检查安全组、监听服务、TLS、代理与云平台接入状态。

**易错边界：** DNS 成功不等于应用可用。

**源码 / 依据：** [deploy/ecs/public-entry.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/public-entry.conf) · [deploy/ecs/nginx.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/nginx.conf)

</details>

### Q105 · L2 · HTTPS、登录和权限控制各解决什么？

<details>
<summary>展开答案与追问</summary>

**口述回答：** HTTPS 保护传输并验证站点身份；登录识别用户；权限控制决定用户能访问哪些资源和动作。三者缺一时，其他机制不能自动补上。

**原理与例子：** 证书正常但后端鉴权错误仍可能越权；登录正常但 HTTP 传输也不符合公开服务预期。

**追问与回答：** 为什么内部端口不直接公开？统一入口更便于 TLS、路由和暴露面管理。

**易错边界：** 不能说“有小锁所以系统安全”。

**源码 / 依据：** [deploy/ecs/public-entry.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/public-entry.conf) · [backend/app/gateway/auth_middleware.py](https://github.com/MHQQysh/rag-project/blob/main/deerflow/backend/app/gateway/auth_middleware.py)

</details>

### Q106 · L2 · 404、502、403 分别怎么排查？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 404 先确认请求是否到正确虚拟主机和路由；502 检查代理上游进程、地址和超时；403 检查应用权限、代理策略或云平台拦截。状态码只是线索。

**原理与例子：** 本次曾观察到 Nginx 404 和阿里云 Beaver 的备案拦截，应看响应内容和服务标识，不要把不同层错误混成同一问题。

**追问与回答：** 服务器里能打开就代表外网能用吗？不代表，内外访问可能经过不同链路。

**易错边界：** 不要在没定位时反复改前端代码碰运气。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [deploy/ecs/public-entry.conf](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/public-entry.conf)

</details>

### Q107 · L2 · 为什么生产环境不用开发服务器？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 开发模式包含热更新、额外监听和调试开销，行为也与生产构建不同。生产部署应使用已构建资源与明确的服务管理方式。

**原理与例子：** 本次前端打包 standalone，并由 systemd 管理前后端。服务管理能负责启动、重启和日志，但不代替数据备份。

**追问与回答：** 源码改完会立即生效吗？前端需要重新构建部署，后端通常需要重启，代理修改要校验再 reload。

**易错边界：** Git push 不等于服务器自动更新。

**源码 / 依据：** [deploy/ecs/build-frontend-wsl.sh](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/build-frontend-wsl.sh) · [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md)

</details>

### Q108 · L2 · 导入完整源码后，上游 CI 会自动在主仓库运行吗？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 不会。GitHub Actions 发现的是仓库根 .github/workflows 下的工作流；导入到 deerflow/.github/workflows 的上游文件只是源码的一部分，不会自动执行。

**原理与例子：** 若要启用上游测试，需要在主仓库工作流中适配 working-directory、依赖缓存和路径触发规则。本次根工作流只增加了面试文档发布，不能因此声称整个 DeerFlow CI 已启用。

**追问与回答：** 保留嵌套工作流有什么用？可以作为上游行为参考与后续迁移基础；正式启用前还应检查权限、secrets 与运行成本。

**易错边界：** 仓库里存在工作流文件，不代表平台已经识别并执行它。

**源码 / 依据：** [docs/UPSTREAM.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/docs/UPSTREAM.md) · [../.github/workflows/commerce-pages.yml](https://github.com/MHQQysh/rag-project/blob/main/.github/workflows/commerce-pages.yml)

</details>

### Q109 · L3 · 以后怎么同步上游又保留自己的改动？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 记录导入基线和个人补丁范围，更新时比较新旧上游，再把个人改动重新应用并回归验证。本次是源码快照导入，不包含上游完整提交历史。

**原理与例子：** 长期维护可用专门同步分支或 subtree 等策略，但必须先明确许可证、冲突解决和部署验证流程。

**追问与回答：** 直接覆盖整个目录好吗？可能丢失演示入口、部署配置和文档，应先审查差异。

**易错边界：** 不能把一次源码复制说成已经建立自动上游同步。

**源码 / 依据：** [README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/README.md) · [docs/UPSTREAM.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/docs/UPSTREAM.md)

</details>

### Q110 · L3 · 怎样设计从 GitHub 到 ECS 的自动部署？

<details>
<summary>展开答案与追问</summary>

**口述回答：** 建议让流水线先测试、构建和打包，产生可识别版本，再通过受控部署凭据发布、健康检查并保留回滚包。运行数据库和真实配置不应被构建包覆盖。

**原理与例子：** 前端构建与服务器运行环境要兼容，发布时还要考虑正在运行的 Agent 任务。当前只有 Pages 自动发布，ECS 应用尚未配置自动部署。

**追问与回答：** 需要把 SSH 私钥写进代码吗？不，应使用受保护的 CI secrets 或更合适的短期凭据。

**易错边界：** 这是一项后续设计，不是本次已经交付的 CI/CD 能力。

**源码 / 依据：** [deploy/ecs/README.md](https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md) · [../.github/workflows/commerce-pages.yml](https://github.com/MHQQysh/rag-project/blob/main/.github/workflows/commerce-pages.yml)

</details>
