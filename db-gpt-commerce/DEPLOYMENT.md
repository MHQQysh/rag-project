# 部署与后端说明

## 现在是否需要后端

网页版不需要自建后端。GitHub Pages 提供 HTML、JS、WASM 与公开模拟数据库。浏览器直接连接 DeepSeek，SQLite 查询在 Worker 中运行，JavaScript 逐条核验明细并精确计算贡献。它可用于项目展示和学习，不适合把私有企业数据库文件直接公开到 Pages。

Python 完整版保留 DB-GPT 官方服务与 AWEL，用于本地学习和后续服务器部署。它和网页版共享口径、数据生成器和对照测试，但运行环境不同；浏览器不运行官方 ReAct 或 AWEL。

## GitHub Pages

仓库 Settings → Pages → Build and deployment → Source 选择 GitHub Actions。Actions 中运行 `Deploy commerce analysis to Pages`；后续 main 分支中本子项目变更会自动构建部署。若提示 Pages 未启用，先完成上述设置，再重新运行工作流。

目标地址：`https://mhqqysh.github.io/rag-project/db-gpt-commerce/`。这是配置对应的目标地址，是否已上线以 GitHub Actions 的成功部署记录为准。

工作流使用 Node.js 22，通过 `npm ci` 和 `npm run build` 运行测试并构建。只上传 `web/dist`；现有两个 Python RAG 项目不会变成可运行的 Pages 后端，也不会被工作流部署。

网页先运行基准演示即可查看结果。真实模式需展开连接设置，输入自己的 DeepSeek API Key；密钥不写入浏览器本地存储。页面使用固定官方 HTTPS 接口，不提供任意转发地址。真实模式会产生 API 费用，网络和服务端跨域策略必须允许直接调用。401 表示密钥失效，402 表示余额不足，429 表示限流；失败会明确显示，不伪装成基准成功。

## 本地预览网页版

需要 Node.js 22 和 Python 3.11 或更高版本。进入 `db-gpt-commerce/web`：

```powershell
npm ci
npm run build
python -m http.server 8080 --directory dist
```

打开 `http://localhost:8080/db-gpt-commerce/`。不要直接双击 index.html：浏览器通常不允许 file 协议加载数据库和 Worker。无需配置本地 `.env` 就能运行基准演示。

## 本机运行完整后端

需要 Git、uv 和可访问依赖仓库的网络；安装脚本通过 uv 创建隔离 Python 3.11 环境。进入本子项目，在 PowerShell 执行：

```powershell
Copy-Item .env.example .env
# 用文本编辑器在本机 .env 填入 OPENAI_API_KEY，切勿提交此文件。
.\Install-Official.ps1
.\Start-DB-GPT.cmd
```

访问 `http://127.0.0.1:5670`。停止使用 `.\Stop-DB-GPT.ps1`。安装会从官方仓库检出固定提交、应用两处兼容补丁，再构建依赖包；没有把庞大的上游副本和虚拟环境提交到本仓库。模型 Key 放在本机 `.env`，完整官方版目前不使用本网页的 Key 输入框。

软件分工：Git 下载源码；uv 安装 Python 与依赖；DB-GPT/FastAPI 运行后台；浏览器打开界面。VS Code 是可选编辑器，不是后端托管服务。具体 Windows 安装步骤与排错见 `LOCAL_README.md`。

## 什么时候才需要买服务器

需要团队共享完整官方界面、接入私有数据库或长期保存用户任务时，才需要持续运行后台的机器。可以先把自己的 Windows 电脑作为仅供本人使用的开发后端。公开访问则建议独立 Linux 云主机部署官方 DB-GPT，并用 Docker Compose 管理服务、Caddy 或 Nginx 提供 HTTPS 与访问入口；实际规格应按数据量与并发测试决定，使用云模型 API 本身不要求 GPU。

后端不是“存一个文件”就能运行：服务器必须持续运行 Python/容器进程。源码放 GitHub；服务配置和模型密钥放服务器环境变量或密钥管理器；数据库及报告放持久化目录/卷并做备份。不要把容器临时文件系统当永久存储，也不要把私有业务库放进 Pages 静态资源。

当前 Windows 完整版只监听回环地址，未提供多租户认证和公开服务限流。本次没有声称已完成公网企业部署。迁移 Linux 前须验证依赖和启动路径，配置认证、CORS、HTTPS、持久化与备份，然后才能公开入口。仅改成 0.0.0.0 不是完整部署方案。

## 两个版本的区别

| 项目 | Pages 网页版 | Python 官方完整版 |
| --- | --- | --- |
| 页面 | 专用经营分析工作台 | 官方 DB-GPT 完整界面 |
| 流程 | JS 固定业务流程 | 官方 Agent 选择工具＋AWEL DAG |
| 数据 | 同源公开模拟 SQLite，浏览器内副本 | 服务端本地 SQLite |
| 核验 | JS 逐条计算与 BigInt 分数 | Python 明细计算与 Fraction |
| 查询约束 | 保守词法检查、query_only、8 秒 Worker 终止 | authorizer 白名单、只读连接和进度预算 |
| Key | 用户当前页面内存 | 服务器/本机 .env |
| 保存 | 用户下载证据 JSON | 服务端 artifacts 目录 |

网页查询检查不等同于 Python 的 authorizer 白名单，更不构成生产数据库授权系统。对公开模拟数据而言，浏览器只处理自己的副本；对真实敏感数据，应由后端执行查询与权限检查。
