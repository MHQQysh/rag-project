# DB-GPT 电商经营分析 Agent

项目学习材料：[完整图文讲解](docs/项目讲解/项目讲解.html) · [技术总述](<docs/项目讲解/01 项目技术总述.md>)。包含架构与调用过程、SQL 口径与独立核验、六种顺序贡献推导、证据复算和面试追问；HTML 可直接用浏览器打开，章节 Markdown 可独立编辑。

已部署**官方 DB-GPT 0.8.2 完整前后端**，在官方对话窗口接入电商数据库与经过校验的 AWEL 分析工具。官方界面提供模型选择、数据源、执行轨迹、任务文件及内嵌报告。

**默认入口已改为 http://127.0.0.1:5670 。** 之前的 5678 自建页面仅为计算验证台，不再作为项目产品前台交付。主界面使用官方仓库自带的已构建前端；电商指标校验、贡献分解和证据报告是本项目扩展。

## 快速使用

1. 双击 **`Start-DB-GPT.cmd`**（旧的 `Start-Commerce.cmd` 也已转到官方入口）。
2. 打开 <http://127.0.0.1:5670>，选择 `deepseek-flash`。
3. 直接输入下面的示例问题。已注册的 `analyze_commerce_revenue` 会执行电商分析，默认基准日期 `2026-09-16`。
4. 如需自由查询表，点击数据库图标选择 `ecommerce`。专用贡献工具无需手动选库。
5. 在官方对话页查看执行步骤、报告预览、任务文件及证据链接。

停止官方服务：`Stop-DB-GPT.ps1`。全新环境安装：`Install-Official.ps1`。完整安装依赖独立保存在 `.official-venv`，锁定文件为 `official-requirements.lock`；不会修改其他项目环境。

官方扩展代码：`run_official.py` 和 `commerce/official_integration.py`。官方源码修补记录：`official-patches/registered-business-tools.patch`，修复注册工具未进入自定义 Agent 提示词及 `execute_tool` 的过期导入路径。

示例问题：

> 上个月华东地区收入下降了，分别分析订单量、客单价、退款和渠道结构的变化；列出各因素的贡献，并输出计算依据。

密钥保存在本项目 `.env`，已被 `.gitignore` 排除。不要把该文件复制进作品展示资料。官方应用只监听 `127.0.0.1:5670`。日期固定是为了复现：数据覆盖 2026-06 至 2026-08，基准日期支持 2026-08 或 2026-09。模型生成对话措辞；核验结论与完整报告来自确定性分析程序。

## 已验证的结果

所有数据均为人工生成的模拟数据，不能解释为真实企业表现。

| 华东指标 | 2026-07 | 2026-08 | 变化 |
|---|---:|---:|---:|
| 支付订单 | 1,000 | 800 | -200 |
| 实付金额 | ¥250,000 | ¥159,000 | -¥91,000 |
| 实付客单价 | ¥250.00 | ¥198.75 | -¥51.25 |
| 当月成功退款 | ¥10,000 | ¥18,000 | +¥8,000 |
| 净收入 | ¥240,000 | ¥141,000 | **-¥99,000（-41.25%）** |

| 因素 | 对净收入变化的贡献 | 占总降幅 |
|---|---:|---:|
| 订单量 | -¥44,800 | 45.25% |
| 渠道结构 | -¥32,775 | 33.11% |
| 渠道内客单价 | -¥13,425 | 13.56% |
| 退款变化 | -¥8,000 | 8.08% |
| 合计 | **-¥99,000** | **100%** |

可观察事实：自营渠道订单从 600 降到 300，订单占比从 60% 降至 37.5%；直播占比从 10% 升至 25%，且直播客单价低于自营。所有渠道内客单价也下降。这些是变化描述，不能据此断言流量、促销或质量导致了收入下降。

## 架构与职责

```text
官方 DB-GPT 对话窗口（5670） / CLI
   ↓
官方 ReAct Agent → analyze_commerce_revenue 领域工具
   ↓
DB-GPT AWEL DAG（commerce/workflow.py）
   resolve_metric_contract → generate_sql → verify_sql → attribute_change
                ↓               ↓                 ↓
         固定期间/地区      DeepSeek / 标准查询     精确 Shapley
                                ↓
                 SQLite 只读执行 + 独立 Python 明细遍历核验
   ↓
HTML 图表报告 + evidence.json + query.sql + parameters.json
```

| 文件 | 用途 |
|---|---|
| `commerce/data.py` | 六表结构、固定种子模拟数据、独立明细聚合 |
| `commerce/query.py` | 标准 SQL、只读授权、预算限制、结果校验 |
| `commerce/analysis.py` | Fraction 精确计算、6 种顺序的 Shapley 分解 |
| `commerce/workflow.py` | 官方 AWEL 节点、真实模型生成和最多一次 SQL 修复 |
| `commerce/config.py` | 本项目环境配置、只读复用 DeerFlow 配置 |
| `commerce/report.py` | 自包含 HTML 报告、版本与证据记录 |
| `commerce/main.py` | FastAPI 页面和报告下载接口 |
| `commerce/cli.py` | 命令行分析与历史证据复算 |
| `tests/test_commerce.py` | 27 项自动化测试 |
| `vendor/DB-GPT` | 固定官方提交 + 已保存的两处兼容补丁 |

## 指标口径

- 数据库金额单位为整数分，展示人民币元；日期按 `Asia/Shanghai` 本地时间解释。
- 实付金额：`orders.status='paid'`，按 `paid_at` 归属月份，不使用下单时间或商品标价。
- 支付订单数：符合上述条件的订单行数；取消/未支付订单排除。
- 实付客单价：实付金额 ÷ 支付订单数，不先扣退款。
- 成功退款：`refunds.status='success'`，按 `refunded_at` 归属月份，连接原订单获取地区与渠道。失败退款排除。
- 地区：订单收货地区快照 `shipping_region`，不是用户当前地区。
- 净收入：当月实付金额 − 当月成功退款。它是该项目经营分析口径，不等同于已确定的会计收入确认规则。
- 边界：`开始日 <= 时间 < 下一月开始日`；允许退款来自更早月份支付的订单。

特意构造的难点：订单均有两条商品明细；同一订单两次退款；6 月订单于 7 月退款；7 月订单于 8 月退款；7 月下单但 8 月支付；失败退款；取消订单；用户当前地区与收货地区不一致。

## 为什么贡献不能简单相加

令 `N` 为支付订单数，`s_c` 为渠道订单占比，`a_c` 为渠道内实付客单价，`R` 为当月成功退款：

```text
净收入 = N × Σ(s_c × a_c) − R
```

对 `N / s / a` 枚举六种替换顺序，每次由上期值切到本期值，记录边际金额变化，再对每项取平均。退款贡献为 `上期 R − 本期 R`。因此四项贡献严格合计到净收入差额，且不依赖人为选择的替换顺序。

总体客单价变化已经由“渠道结构 + 渠道内客单价”共同解释，不能再额外加一次“总体客单价贡献”。计算使用 `Fraction`，证据里保存每次替换的精确分数；网页金额四舍五入到分。不同数据下展示四舍五入可能产生尾差，精确合计以证据为准。

若一个渠道仅一期间没有订单，其缺失客单价借用另一期间值；两期均无订单取零并披露。若整个月无订单，则分解不可识别，拒绝出具这套贡献结论。该分解是描述性的，不建立因果关系。

## SQL 正确性与失败处理

1. SQLite `mode=ro`、`query_only`、authorizer 限制到业务表和聚合函数；只允许单条 SELECT/WITH。
2. 运行有 3 秒/200 万虚拟机指令预算、100 行上限，禁止随机大对象、系统表、扩展加载与写操作。
3. 结果必须为每个期间、每个渠道唯一一行，列名与整数分类型固定。
4. **独立核验不使用生成 SQL**：另行读订单和退款原始行，通过 Python 遍历计算期望结果，逐项相等才接受。
5. 模型 SQL 错误允许携带校验错误修复一次；仍错误则返回失败并保存尝试，不静默使用标准 SQL 冒充模型成功。
6. 固定分析问题范围为地区月度收入变化；它不是任意业务问题的通用问答器。产品、用户细分、因果诊断等需要新定义指标与核验器。

校验结论只对本次数据快照和支持的指标成立，不宣称证明任意 SQL 在所有数据库上的语义正确。

## 复现环境

本机已有 Python 3.13 和其他应用。官方核心包固定 `aiohttp==3.8.4`，因此使用独立 **Python 3.11.14** 环境，避免修改已有依赖。WSL Ubuntu 已存在但本次启动失败，当前方案不依赖 WSL 或 Docker。

- 官方源码：<https://github.com/eosphoros-ai/DB-GPT>
- 固定提交：`ca9f014cb3ead157ca2ee6ce645658f5fb55138c`
- 官方包：`dbgpt==0.8.2`
- 参考官方示例：`examples/awel/simple_nl_schema_sql_chart_example.py`
- 依赖固定在 `requirements.lock`；官方 core 从固定源码构建普通 wheel 安装。Windows 中文路径下 editable 安装未能正确解析 `.pth`，因此未采用 editable 运行。
- 当前模型：`deepseek-flash`，通过 DeepSeek OpenAI 兼容 API；SQL 生成关闭 thinking，避免思考内容耗尽输出预算。

新机器安装官方完整应用（已有 Git 和 uv）：

```powershell
cd 'E:\大四上\RAG项目\db-gpt-commerce'
powershell -ExecutionPolicy Bypass -File .\Install-Official.ps1
```

如果配置 `.env`，优先使用 `OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL`。否则只读查找 `../deer-flow/config.yaml`、`../deer-flow/.env` 和 `../deer-flow/.deepseek.env`。密钥不写入报告或模型调用轨迹。

```powershell
$env:PYTHONUTF8='1'
# 标准基准
.venv\Scripts\python.exe -m commerce.cli --mode reference
# 真实模型
.venv\Scripts\python.exe -m commerce.cli --mode live
# 另一个月份与地区
.venv\Scripts\python.exe -m commerce.cli --mode reference --as-of 2026-08-16 --region 华北
# 测试
.venv\Scripts\python.exe -m pytest tests -q
# 重算实际运行证据（也可替换成页面上运行编号对应的目录）
.venv\Scripts\python.exe -m commerce.cli --replay artifacts/1fc2d34e32f24aa4b14707cd6d76f0f6/evidence.json
```

每次运行都有唯一目录 `artifacts/<run_id>/`。证据包括数据库 SHA256、数据种子与覆盖范围、官方提交、业务代码指纹、Python 版本、SQL、绑定参数、模型请求与输出（不含密钥）、SQL 结果、独立核验结果、六种排列的计算记录以及工作流轨迹。数据保存在 `data/commerce.sqlite`，首次自动生成，后续启动不覆盖。

## 演示与讲解顺序

1. 先看净收入下降 41.25%，明确“下降”来自实际计算而不是用户问题中的预设。
2. 展示订单量、渠道结构、渠道内客单价、退款四项贡献，核对合计。
3. 展开 SQL，解释为什么支付与退款先分别聚合，订单明细为何不能直接连进金额求和。
4. 打开证据，解释模型查询与独立明细遍历的双路径验证。
5. 展示跨月退款、重复连接拒绝测试和命令行复算。
6. 明确当前没有证据证明“流量减少”或“商品质量下降”，列出下一步需要的数据。

验证记录见 `VALIDATION.md`。复现材料包含源码与固定数据生成器；证据包下载不包含 API 密钥、Python 环境或整份官方仓库。

## 官方界面集成的边界

- 经营分析工具已连接真实模型、数据库与本地报告文件。报告通过官方 `html_interpreter` 的文件模式加载，避免让模型重新抄写数值。
- 通用 SQL、任意代码、文件分析是官方能力，不自动获得本项目专用指标的核验保证；电商贡献问题使用 `analyze_commerce_revenue`。
- 当前配置了 DeepSeek 文本模型，尚未配置知识库向量模型；知识库语义检索需要另行配置 embeddings。首页官方其他示例也可能需要其对应数据和环境。
- `official-data/ecommerce.sqlite` 为注册到官方产品的数据副本；`data/commerce.sqlite` 保留原始基准。官方状态、会话和运行数据位于 `official-data/`。
