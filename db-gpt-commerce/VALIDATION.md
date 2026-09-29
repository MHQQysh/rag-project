# 验证记录 · 2026-09-16

## 最终交付：官方完整前后端

- 官方服务 `http://127.0.0.1:5670` 已运行，DeepSeek worker 健康，官方首页、对话与报告面板正常。
- `ecommerce` SQLite 数据源已注册；专用 AWEL 分析以 `analyze_commerce_revenue` 工具接入官方 ResourceManager。
- 最终浏览器会话 `46a02b22-2f9d-4a47-89dc-df620fb18868`：输入原始中文问题，自动调用专用工具，再用 `html_interpreter(file_path=...)` 加载已核验文件；2/2 步完成，无失败步骤。
- 最终分析证据编号 `c8721115df704349a4b89febde64a859`；净收入 -99000 元，四项贡献合计一致，原生报告自营客单价显示 300→280 元。
- 官方完整环境 210 个包依赖检查通过。`Start-DB-GPT.ps1` / `Stop-DB-GPT.ps1` 已实际验证。
- 官方源码有两处可复现补丁：注册业务工具提示词遗漏、execute_tool 的旧导入路径。补丁保存在 official-patches/registered-business-tools.patch，反向检查通过。
- 回归测试：`.official-venv/Scripts/python.exe -m unittest discover -s official_tests -v`，覆盖注册工具间接调用、HTML 文件数值不改写。
- 原生知识库 embeddings 尚未配置；没有宣称所有官方示例及可选能力均已配置验证。

## 前期计算验证台记录（历史）

- 官方源码提交 `ca9f014cb3ead157ca2ee6ce645658f5fb55138c`；`git status --short` 为空。
- Windows 原生 Python 3.11.14，官方 `dbgpt==0.8.2` 可导入；AWEL 两节点烟雾测试输出 6，业务 DAG 五步轨迹完整。
- `python -m pytest tests -q`：**27 passed**。有一条 FastAPI/Starlette 测试客户端依赖的弃用警告，不影响运行。
- 标准 SQL 和真实 DeepSeek SQL 均通过独立明细核验，收入从 240000 元降到 141000 元。
- 真实模型成功运行：`1fc2d34e32f24aa4b14707cd6d76f0f6`。
- 浏览器真实模型运行：`54059c9ddc584eb191c4e16971cd3217`；页面可见“模型 SQL · 核验通过”、四项贡献和渠道对照。
- 最终版本浏览器真实模型运行：`aa41625eb0c84b3693fb4f2698987c50`；报告补齐渠道内客单价，缺失客单价可正常显示并披露。
- 启停脚本均已实际执行；服务重新启动成功。报告和日志的密钥扫描通过。
- `python -m commerce.cli --replay artifacts/1fc2d34e32f24aa4b14707cd6d76f0f6/evidence.json`：SQL、数据库 SHA256 与贡献结果一致。
- HTTP 测试覆盖首页、分析、HTML 报告、证据 ZIP、错误日期返回 422、非法报告路径返回 404。

## 修复的实际问题

1. Python 3.13 与官方旧 aiohttp 依赖不适配：采用隔离的 Python 3.11。
2. 中文路径的 editable `.pth` 未生效：从官方源码构建普通 wheel，不改官方源文件。
3. AWEL 导入需要 cloudpickle：加入锁定依赖。
4. DeepSeek 首次调用 3500 completion tokens 全部进入 reasoning，content 为空：记录为失败，按已有配置关闭 SQL 生成的 thinking，后续真实调用成功；未伪造输出。

## 前期版本边界（官方界面部署前）

- 当前交付 AWEL 驱动的业务应用，未部署官方完整后台。
- 模型只负责受约束的 SQL 生成；分解、图表和事实报告由确定性代码生成。
- 模拟数据、固定地区和月份；不等同于接入任意企业生产数据库的完整平台。
- 真实模型有调用延迟和费用，服务不可用时明确报错。
