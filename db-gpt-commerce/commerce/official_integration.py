"""Register the verified commerce workflow in the upstream DB-GPT agent toolbox."""

import json
import shutil

from dbgpt.agent.resource.tool.base import tool
from fastapi import APIRouter

from .data import DB_PATH, ROOT, seed_database

OFFICIAL_DB = ROOT / "official-data" / "ecommerce.sqlite"


@tool(
    description=(
        "分析模拟电商华东/华北地区上个月净收入变化，拆解订单量、渠道结构、渠道内客单价、退款贡献，"
        "生成真实模型 SQL 并独立核验、保存完整 HTML 报告和计算证据。"
        "电商收入下降分析必须优先使用此工具，避免多表重复计数。"
        "模拟数据覆盖2026年6月至8月；默认分析基准2026-09-16，即比较8月与7月。"
        "返回verified才可声称已验证；结果是算术分解而非因果结论。"
        "工具返回render_tool_call：必须直接按其file_path用html_interpreter展示已生成报告，禁止重写HTML中的数值。"
    )
)
async def analyze_commerce_revenue(region: str = "华东", as_of: str = "2026-09-16") -> str:
    """Run the audited ecommerce income analysis.

    Args:
        region: Shipping region, 华东 or 华北.
        as_of: Date determining the prior two complete months, YYYY-MM-DD.
    """
    from .workflow import AnalysisRequest, run_analysis

    request = AnalysisRequest(
        region=region,
        as_of=as_of,
        mode="live",
        question=f"上个月{region}地区收入变化，分析订单量、客单价、退款和渠道结构贡献，并输出计算依据。",
    )
    result = await run_analysis(request, path=OFFICIAL_DB)
    base = f"http://127.0.0.1:5670/commerce/reports/{result['run_id']}"
    a = result["analysis"]
    return json.dumps(
        {
            "status": result["status"],
            "run_id": result["run_id"],
            "periods": result["params"],
            "currency": "CNY",
            "money_unit": "cents (divide by 100 to display yuan)",
            "totals": a["totals"],
            "delta_cents": a["delta_cents"],
            "change_pct": a["change_pct"],
            "factors": a["factors"],
            "channels": a["channels"],
            "formula": a["formula"],
            "interpretation": a["interpretation"],
            "hypotheses": a["hypotheses"],
            "reconciliation_cents": a["reconciliation_cents"],
            "sql": result["sql_attempts"][-1]["sql"],
            "report_url": base + "/report.html",
            "evidence_url": base + "/evidence.json",
            "download_url": base + "/bundle.zip",
            "render_tool_call": {
                "tool": "html_interpreter",
                "arguments": {
                    "file_path": str(ROOT / "artifacts" / result["run_id"] / "report.html"),
                    "title": f"{region}经营分析 · 已核验",
                },
            },
            "instruction": "下一步按render_tool_call原样调用html_interpreter(file_path=实际绝对路径,title=标题)，不要使用html参数重写报告，不要猜路径或通过shell/Python下载。然后terminate，列出金额贡献和计算口径，附报告和证据链接；不要把待验证假设写成原因。",
        },
        ensure_ascii=False,
    )


def install(server):
    seed_database()
    OFFICIAL_DB.parent.mkdir(parents=True, exist_ok=True)
    if not OFFICIAL_DB.exists():
        shutil.copy2(DB_PATH, OFFICIAL_DB)
        shutil.copy2(DB_PATH.with_suffix(".meta.json"), OFFICIAL_DB.with_suffix(".meta.json"))
    # Register before upstream's catch-all static mount.
    from .main import artifact

    router = APIRouter()
    router.add_api_route("/commerce/reports/{run_id}/{filename}", artifact, methods=["GET"])
    server.app.include_router(router)
    original = server.initialize_app

    def initialize_with_commerce(param, args=None):
        result = original(param, args)
        from dbgpt.agent.resource.manage import get_resource_manager
        from dbgpt_serve.datasource.manages.connect_config_db import ConnectConfigDao

        get_resource_manager(server.system_app).register_resource(resource_instance=analyze_commerce_revenue)
        dao = ConnectConfigDao()
        if not dao.get_by_names("ecommerce"):
            dao.add_file_db(
                db_name="ecommerce",
                db_type="sqlite",
                db_path=str(OFFICIAL_DB),
                comment="模拟电商经营数据，2026-06至08；收入按支付月份实付减成功退款发生月；地区取shipping_region。分析贡献优先调用analyze_commerce_revenue工具。",
            )
        return result

    server.initialize_app = initialize_with_commerce
