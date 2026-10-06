# YSH ECS 部署

这是当前运行环境的可审查配置快照，不含运行数据库、密钥或二进制依赖。完整原版源码位于主仓库的 deerflow/ 子目录；以下命令以该子目录为项目根。

## 已同步的改动

- `public-entry.conf`：HTTPS 反向代理、HTTP 跳转 HTTPS、首页 `/` 跳转 `/login`。
- `nginx.conf`：本机 2026 入口和公共配置 include；上游端口 3000、8001。
- 两个 `.service`：前后端 systemd 服务，包含当前内存限制。
- `config.example.yaml`：服务器模型、工具、沙箱及并发配置；密钥使用环境变量引用。
- `backend/packages/harness/deerflow/community/aio_sandbox/backend.py`：沙箱启动等待 60 秒改为 180 秒。

## 恢复部署的顺序

1. Ubuntu 安装 Docker、Redis、Nginx、Certbot、Python 3.12 与 uv。源码放在 `/opt/deerflow`。
2. 在 backend 目录执行 `uv sync --frozen --no-dev --extra redis`，安装锁定依赖。
3. 复制本目录 `config.example.yaml` 到 `/opt/deerflow/config.yaml`；复制根目录 extensions 示例到实际 extensions 配置。
4. 在内存充足的 Linux/WSL 构建机执行 `bash deploy/ecs/build-frontend-wsl.sh`，然后执行 `bash deploy/ecs/package-frontend-wsl.sh`。打包包含构建机 Node，构建机与服务器需同为 Linux x86_64。将生成包解压至 `/opt/deerflow/frontend-runtime`。
5. 在服务器创建 `/etc/deerflow/model.env`（参考示例）与 `/etc/deerflow/runtime.env`（参考示例）。三个认证 secret 必须分别随机生成，不能使用示例占位值。文件权限 600。
6. 将两个 service 文件安装到 `/etc/systemd/system/`。`systemctl daemon-reload` 后启动 Redis 和两个服务。
7. 为你自己的域名配置 DNS 和 80/443 入站规则，先配置 HTTP ACME webroot，再用 Certbot 签发证书。本目录 HTTPS 配置依赖证书已存在，不能先启用。
8. 备份现有 Nginx 配置，再安装本目录 nginx.conf 和 public-entry.conf 到对应路径；自有域名需同时替换证书路径、server_name、跳转地址及可信来源。执行 `nginx -t`，通过后 reload。
9. 开启 certbot.timer，并配置续期 deploy hook 执行 `systemctl reload nginx`。
10. 验证 HTTPS 登录页和 `/health/ready`；首次新部署需创建管理员。已有实例保留 `/var/lib/deerflow`，不能覆盖数据库。

这些步骤为迁移说明，不是已经在空白机器验证的一键安装器。当前实例的部署与端到端验证见 [部署说明](部署说明.md)。

## 后续修改与发布

以本仓库作为改动记录：修改 → 验证 → Git commit/push → 部署对应文件。前端改动要重新构建；后端改动重启 Gateway；Nginx 改动通过 `nginx -t` 后 reload。主仓库的 GitHub Pages 自动发布静态页面；ECS 应用没有配置自动部署，因此 push 不会自动更改线上 Agent。

服务端真实配置、用户聊天和密钥不从 GitHub 覆盖。云端紧急修复需回填这里，避免代码与部署不一致。

## 一键演示入口

登录页的“进入演示”按钮调用服务端 `/api/v1/auth/login/demo`，不会向浏览器提供密码。演示账号无密码、非管理员；共享历史和文件。后台保持管理员登录独立，禁止演示账号修改身份或创建长期访问令牌。

默认关闭。当前 ECS 可在 backend 工作目录用虚拟环境执行本目录 `provision-demo.py`（先核对其中的演示邮箱）；脚本使用已有数据库 API 创建普通用户，将 ID 和开关写入受保护的 runtime.env。重启 Gateway 后生效。新机器必须已初始化管理员和数据库。不要将真实 runtime.env 提交 Git。

关闭方法：将 `DEER_FLOW_DEMO_LOGIN_ENABLED=false` 写入 runtime.env，重启 Gateway；已有演示会话也会被拒绝。演示访问会使用服务器配置的模型额度。

### 2026-10-06 验证记录

- 登录/认证/CSRF 相关回归：183 项通过；演示按钮交互：3 项通过。
- 前端 `pnpm check` 和生产构建通过。后端改动通过 Ruff。
- 在 ECS 通过 HTTPS 域名实测：demo-status、演示登录、普通用户身份、创建/读取/删除验收对话正常；MCP 管理配置与修改密码返回 403。
- 本机外网观察到阿里云 `Server: Beaver` 返回 `Non-compliance ICP Filing`，同时部分 HTTPS 连接重置；服务器内通过域名访问正常。这是待核查的公网接入问题，不能把服务器内验证等同于所有访客均可访问。
- 全量后端基线最初因本地配置缺少模型环境变量而无法收集；补测试占位变量后，全量套件运行约 6 分钟后主动停止；截至停止 3077 项通过、25 项跳过，未将其声明为完整通过。相关功能测试结果如上。
