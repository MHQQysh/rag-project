# Commerce Lens 电商经营分析

可在 GitHub Pages 打开的电商分析子项目，同时保留基于官方 DB-GPT 的 Python 完整版本。

**[打开网页版](https://mhqqysh.github.io/rag-project/db-gpt-commerce/)** · **[部署与后端说明](DEPLOYMENT.md)** · **[逻辑讲解](docs/项目讲解/项目讲解.html)** · **[本地官方版安装](LOCAL_README.md)**

新增：[与 DeerFlow 的架构及代码对比](docs/项目讲解/06%20DeerFlow与DB-GPT对比.md) · [同服务器部署与维护](CLOUD_DEPLOYMENT.md) · [云端验收记录](CLOUD_VALIDATION.md)。官方云端版和 GitHub Pages 浏览器版是独立入口；云端域名暂缓配置，当前通过 SSH 隧道访问。

## 先用起来

网页版点击“运行基准演示”，不用 Key 即可查看真实计算的订单、退款和贡献。展开 DeepSeek 设置，输入自己的 API Key，再点击“使用 DeepSeek 分析”，调用真实模型生成 SQL；结果必须通过独立明细核验，失败最多修复一次。Key 只存在当前页面内存，不保存到 GitHub 或浏览器本地存储。

数据覆盖 2026 年 6—8 月，支持华东、华北及七月/八月环比分析。所有数据为公开模拟样本。它是完整可运行的限定场景作品，不是任意企业数据都能直接接入的生产平台。

## 一句话理解代码

**模型写查询，程序核对查询结果，程序算贡献，页面解释和展示。**

```text
网页选择地区和月份
  → 固定支付月、退款发生月、地区快照口径
  → DeepSeek 返回 SQL（或明确选择标准基准）
  → Worker 内 SQLite 执行
  → JavaScript 遍历原始订单与退款独立对账
  → BigInt 精确分数计算六种顺序平均贡献
  → 图表、渠道明细、SQL 尝试、证据 JSON 下载
```

Python 完整版在最外层还有“官方 DB-GPT 对话 Agent 选择工具”，工具内部由 AWEL 执行四节点。网页版直接调用专用流程，不声称在浏览器里运行了 Python AWEL。

## 目录怎样读

| 文件或目录 | 负责什么 |
| --- | --- |
| web/index.html、styles.css | 页面与排版 |
| web/app.mjs | 操作、流程、取消、图表、下载 |
| web/model.mjs | DeepSeek 请求和输出检查 |
| web/query-worker.js | 隔离执行 SQLite 查询 |
| web/core.mjs | 标准查询、独立核验、精确贡献算法 |
| web/assets、web/tests | 公开模拟数据与 Python 对照测试 |
| commerce/workflow.py | 本地 AWEL 编排与模型修复 |
| commerce/query.py | Python 查询约束和核验 |
| commerce/analysis.py | Python Fraction 贡献分解 |
| commerce/data.py | 数据生成、口径、独立明细基准 |
| commerce/official_integration.py | 官方工具接入 |
| commerce/report.py | 服务端证据和 HTML 报告 |
| scripts/export_web.py | 从生成器重新导出公开样本 |
| official-patches、official_tests | 上游兼容修补和桥接测试 |
| docs、DEPLOYMENT.md | 深度讲解及两种运行环境的部署说明 |

## 已实现的工程内容

- 收入口径按支付时间、退款按成功发生月、地区按订单历史快照。
- SQL 与明细双路径计算，识别重复计数、错误月份、重复渠道和金额。
- 网页单条查询限制、SQLite query_only、结果上限与 8 秒 Worker 终止；Python 版另有 authorizer 白名单。
- 真实模式最多一次 SQL 修复；失败明确报错，不拿标准答案冒充模型结果。
- 精确分数贡献分解，保留六种顺序和证据；贡献可对账，不是业务因果。
- GitHub Actions 构建、测试与静态发布；脚本同源加载，不提交真实密钥。

华东八月对七月：净收入从 240,000 元降到 141,000 元。订单量、渠道结构、渠道内客单价、退款贡献分别为 −44,800、−32,775、−13,425、−8,000 元，合计 −99,000 元。

## 是否要部署后端

**当前 Pages 演示不需要服务器。**浏览器运行公开模拟库和计算，只有 DeepSeek 是远程 API。

需要官方完整界面或私有数据库时，先在 Windows 电脑运行 Python 版；准备 Git 和 uv，执行 `Install-Official.ps1`，在 `.env` 配置 Key，运行 `Start-DB-GPT.cmd`。服务监听本机 5670 端口。

需要多人公网访问时，再单独部署后台，并配置认证、HTTPS 和持久化。不要把企业数据库上传到 Pages。软件分工与步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 验证与来源

进入 web，运行 `npm ci` 和 `npm run build`。测试比较四组地区/月度数据与 Python 输出，覆盖错误聚合、跨月退款、零订单、查询拒绝、API 错误与密钥不进入返回记录。

历史 Python 验证见 [VALIDATION.md](VALIDATION.md)，网页版验证见 [WEB_VALIDATION.md](WEB_VALIDATION.md)。不能用旧本地模型成功替代新网页版真实模型验证。

官方框架：[eosphoros-ai/DB-GPT](https://github.com/eosphoros-ai/DB-GPT)，固定提交 `ca9f014cb3ead157ca2ee6ce645658f5fb55138c`，由安装脚本获取并保留上游许可。浏览器 SQLite 使用 MIT 许可的 sql.js 1.14.1，发布文件附带许可。本子项目新增电商业务实现、浏览器移植、验证和文档。
