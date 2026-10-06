# DB-GPT 云端部署与维护

本部署使用已有 DeerFlow 的 Ubuntu 服务器，安装官方 DB-GPT 0.8.2 界面与电商分析工具。域名按用户要求稍后配置；此阶段只监听服务器本机 `127.0.0.1:5670`，通过 SSH 隧道访问，不开放裸露的公网分析接口。

## 你需要安装什么软件

服务器已具备 Linux、systemd、Nginx 和 DeerFlow 环境。DB-GPT 另用 Python 3.11 与独立虚拟环境，不需要 GPU，也不需要在电脑上再启动 Python 后端。模型调用 DeepSeek API，沿用服务器已有的模型凭据，凭据不会写进代码仓库。

在已经可以连接这台服务器的 Windows 电脑上，只需要现有的 OpenSSH 和浏览器。执行本目录的 `deploy/Open-Cloud-DB-GPT.ps1`，脚本在后台建立加密隧道，再打开 `http://127.0.0.1:25670/`。网址看起来是本地地址，实际页面、数据库和模型调用都在云服务器上运行；电脑关机只会断开隧道，不会停止云端服务。首次换电脑要配置自己的 SSH 访问凭据，不要把私钥放进 GitHub。

## 服务和数据各在哪里

| 内容 | 服务器位置 | 作用 |
|---|---|---|
| 应用源码 | `/opt/dbgpt-commerce` | 官方启动入口、电商业务代码 |
| 官方固定版本源码 | `/opt/dbgpt-commerce/vendor/DB-GPT` | 构建包、官方页面、模板；包含两处桥接补丁 |
| Python 运行环境 | `/opt/dbgpt-commerce/.official-venv` | 与 DeerFlow 的 Python 包隔离 |
| Python 解释器 | `/opt/dbgpt-python` | 服务账号可读取，不依赖 root 私有目录 |
| 模型配置 | `/etc/dbgpt-commerce/model.env` | root 可读的环境文件，由 systemd 注入；不提交仓库 |
| 会话及官方工作目录 | `/var/lib/dbgpt-commerce/official-data` | DB-GPT 元数据库、工作文件、持久化加密密钥 |
| 模拟基础数据 | `/var/lib/dbgpt-commerce/data` | 命令行使用的模拟电商数据 |
| 官方注册的模拟库 | `/var/lib/dbgpt-commerce/official-data/ecommerce.sqlite` | 官方业务工具使用的数据库副本 |
| 分析报告和证据 | `/var/lib/dbgpt-commerce/artifacts` | 每个运行编号一个目录 |
| 系统服务 | `/etc/systemd/system/dbgpt-commerce.service` | 后台运行、开机启动、失败重启与资源限制 |

`/opt/dbgpt-commerce` 里的对应数据目录是指向 `/var/lib/dbgpt-commerce` 的符号链接。代码与可变数据分开，是为了升级代码时保留历史分析和会话。备份应包含整个 `/var/lib/dbgpt-commerce` 和受保护的 `/etc/dbgpt-commerce`，尤其不要遗失持久化加密密钥。

## 日常管理

以下命令在服务器终端执行：

```bash
systemctl status dbgpt-commerce --no-pager
journalctl -u dbgpt-commerce -n 80 --no-pager
systemctl restart dbgpt-commerce
systemctl stop dbgpt-commerce
systemctl start dbgpt-commerce
```

DeerFlow 仍使用 `deerflow-gateway` 与 `deerflow-frontend` 服务。DB-GPT 的重启命令不会重启它们。

当前 DB-GPT 配置：普通 Linux 服务账号运行、监听回环地址、无提权能力、私有临时目录；内存硬上限 700 MiB（不启用软限制，避免加载期反复回收导致卡顿）、最多 512 MiB swap、CPU 上限一个核。达到硬限制可能终止当前分析并触发重启，因此长任务要检查实际资源情况。这些限制用于控制同机影响，不等价于多租户沙箱隔离。

云端设置 `COMMERCE_LAZY_CODE_SERVER=1`：跳过官方 Lyric 代码执行进程的启动预热，在首次真正执行代码时仍走官方初始化流程。电商 SQL、独立核验和原始 HTML 报告不需要这组进程；这项适配位于 `commerce/cloud_runtime.py`，有延迟初始化与实际执行入口的回归测试。分词缓存固定在持久化 cache 目录，避免重启后重复下载。

服务器只有约 1.6 GB 内存。DeerFlow 的沙箱也会消耗内存，建议作品演示时一次运行一个重任务。不要把两套服务能启动理解成已经通过并发容量测试。

## 重建安装的步骤

下面是维护人员的重建步骤，当前服务器不需要重复安装。

1. 在本地准备固定提交的官方源码，并应用 `official-patches/registered-business-tools.patch`。
2. 用 `deploy/package-source.py --vendor <官方源码目录> --output <压缩包路径>` 导出源码包。它不会打包项目 `.env`、本地虚拟环境、会话数据和模型密钥。
3. 上传并解压到新的 `/opt/dbgpt-commerce` 目录；不要直接覆盖旧实例的数据目录。
4. 以 root 运行 `deploy/install-linux.sh`。脚本使用现有 `/opt/deerflow-tools/bin/uv`，安装独立解释器、锁定依赖及七个官方包；Windows 专用依赖在 Linux 上排除。当前默认使用阿里云 PyPI 镜像，可通过 UV_DEFAULT_INDEX 改回其他受信的软件源。
5. 用已有 DeerFlow Python 环境运行 `deploy/prepare-service.py`。脚本从现有 DeepSeek 配置生成独立密钥文件，建立服务账号、数据路径和 systemd 服务，不修改 DeerFlow 配置。
6. `systemctl enable --now dbgpt-commerce`，再验证页面、模型、业务工具与报告。

这些脚本针对当前服务器目录编写，不是任何云服务器都能直接通用的一键安装器。迁移时需要调整 uv 路径、DeepSeek 配置来源以及 SSH 目标。

## 域名准备好后怎样上线

计划地址为 `https://dbgpt.shihongyuan.cn`。域名未完成前，不把这个地址描述成已经上线。

1. 在 DNS 中添加 `dbgpt` 的 A 记录，指向与 DeerFlow 相同的服务器。
2. 增加独立 Nginx 站点，代理到 `127.0.0.1:5670`，保留 SSE 流式响应并设置足够的读取超时。
3. 为新域名申请 HTTPS 证书。
4. **正式暴露公网前添加访问认证。**当前官方配置没有启用完整的公网用户隔离；SSH 隧道承担访问控制。不能只做反向代理就把模型和代码执行入口公开给所有人。个人演示可使用 Nginx Basic Auth 配合 HTTPS；多人正式使用还需应用层身份、数据授权与任务隔离。
5. 确认域名具备云服务商要求的公网接入条件。另一个 DeerFlow 会话在 2026-10-06 已记录该域名的备案拦截；仅添加 DNS 不能保证外网可访问。应先在云控制台处理该问题，再进行公网验收。
6. 将官方 CORS 允许来源加入新域名；如需完整绝对报告地址，在环境文件里设置 `COMMERCE_PUBLIC_BASE_URL=https://dbgpt.shihongyuan.cn`。默认相对报告链接可跟随当前访问地址。
7. 验证登录保护、真实分析、报告下载、重启后历史数据，并确认原 DeerFlow 仍可访问。

本次没有修改已有 `deerflow.shihongyuan.cn` 的入口，也没有把 DB-GPT 部署进 GitHub Pages。Pages 继续提供浏览器演示版，两者通过文档明确区分。

## 尚未配置的功能

当前只配置了 DeepSeek 对话模型，没有配置 embedding 模型。官方服务会提示数据库向量摘要不可用；知识库向量检索与依赖该摘要的通用数据聊天，不在本次可用范围。电商业务工具直接使用明确 schema、只读 SQL 和独立明细核验，不依赖向量摘要。需要知识库功能时，应另行接入向量模型并做相应验证。
