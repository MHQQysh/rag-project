import html
import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from .data import ROOT, digest

ARTIFACTS = ROOT / "artifacts"


def upstream_commit():
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT / "vendor/DB-GPT"), "rev-parse", "HEAD"], text=True, timeout=5
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def provenance(path):
    modules = {p.name: digest(p) for p in sorted((ROOT / "commerce").glob("*.py"))}
    metadata_path = path.with_suffix(".meta.json")
    return {
        "database_sha256": digest(path),
        "dataset": json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {},
        "upstream_commit": upstream_commit(),
        "framework": "DB-GPT AWEL",
        "dbgpt_version": version("dbgpt"),
        "python": platform.python_version(),
        "business_source_sha256": modules,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def render_report(result: dict) -> str:
    a = result["analysis"]
    esc = lambda x: html.escape(str(x))
    money = lambda cents: "—" if cents is None else f"¥{cents / 100:,.2f}"
    prev, cur = a["totals"]["previous"], a["totals"]["current"]
    bars = ""
    maximum = max(abs(f["cents"]) for f in a["factors"]) or 1
    for f in a["factors"]:
        bars += f'<div class="barrow"><b>{esc(f["name"])}</b><div class="track"><div style="width:{abs(f["cents"]) / maximum * 100:.2f}%;background:{"#b64b43" if f["cents"] < 0 else "#197568"}"></div></div><span>{money(f["cents"])}</span></div>'
    channel_rows = "".join(
        f"<tr><td>{esc(c['channel'])}</td><td>{c['previous']['order_count']} → {c['current']['order_count']}</td><td>{c['previous']['share_pct']:.1f}% → {c['current']['share_pct']:.1f}%</td><td>{money(c['previous']['aov_cents'])} → {money(c['current']['aov_cents'])}</td><td>{money(c['previous']['paid_cents'])} → {money(c['current']['paid_cents'])}</td><td>{money(c['previous']['refund_cents'])} → {money(c['current']['refund_cents'])}</td></tr>"
        for c in a["channels"]
    )
    metrics = "".join(
        f'<div class="metric"><small>{label}</small><strong>{money(cur[key]) if key != "order_count" else cur[key]}</strong><span>上期 {money(prev[key]) if key != "order_count" else prev[key]}</span></div>'
        for label, key in [
            ("净收入", "net_cents"),
            ("支付订单", "order_count"),
            ("实付客单价", "aov_cents"),
            ("成功退款", "refund_cents"),
        ]
    )
    hypotheses = "".join(f"<li>{esc(x)}</li>" for x in a["hypotheses"])
    attempts = "".join(
        f"<details><summary>SQL 尝试 {i + 1} · {esc(t.get('status', 'generated'))}</summary><pre>{esc(t['sql'])}</pre><p>{esc(t.get('error', ''))}</p></details>"
        for i, t in enumerate(result["sql_attempts"])
    )
    change = f"{a['change_pct']:+.2f}%" if a["change_pct"] is not None else "基期为零，比例不可定义"
    notes = "；".join(a["imputation_notes"]) or "本次无缺失渠道客单价填补。"
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>经营分析报告</title>
<style>body{{font:15px/1.7 system-ui,"Microsoft YaHei",sans-serif;color:#183331;background:#f4f5ef;margin:0}}main{{max-width:1040px;margin:auto;padding:48px 28px}}h1{{font-size:34px;margin:10px 0}}h2{{margin-top:30px}}.eyebrow{{color:#197568;letter-spacing:2px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.metric,section{{background:white;border:1px solid #dfe5dc;border-radius:14px;padding:20px}}.metric strong,.metric span{{display:block}}.metric strong{{font-size:24px}}small,.muted{{color:#647671}}section{{margin-top:20px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px 8px;text-align:left;border-bottom:1px solid #e5e9e1}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f1;padding:15px;font-size:12px}}.barrow{{display:grid;grid-template-columns:110px 1fr 130px;gap:16px;align-items:center;margin:18px 0}}.track{{background:#f2ede6;height:18px;border-radius:4px;overflow:hidden}}.track div{{height:100%}}@media(max-width:700px){{.cards{{grid-template-columns:1fr 1fr}}main{{padding:20px 12px}}section{{overflow:auto}}}}</style>
<main><div class="eyebrow">COMMERCE INTELLIGENCE / DB-GPT AWEL</div><h1>{esc(result["params"]["region"])}经营月报</h1>
<p>{esc(result["params"]["current_start"])} 至 {esc(result["params"]["end"])}（不含结束日），对比上一自然月 · 模拟数据</p>
<p><b>{"真实模型 SQL" if result["request"]["mode"] == "live" else "标准 SQL 基准"} · 已通过独立明细核验</b></p><div class="cards">{metrics}</div>
<section><h2>净收入变化 {money(a["delta_cents"])} <small>({change})</small></h2>{bars}<p>{esc(a["formula"])}</p><p>{esc(a["interpretation"])}</p><p>贡献合计与净收入变化差额：{money(a["reconciliation_cents"])}。{esc(notes)}</p></section>
<section><h2>渠道对照</h2><table><thead><tr><th>渠道</th><th>订单量</th><th>订单占比</th><th>渠道内客单价</th><th>实付金额</th><th>退款</th></tr></thead><tbody>{channel_rows}</tbody></table></section>
<section><h2>计算口径</h2><p>金额按人民币计算；原始数据库以分存储。支付时间归属收入月份，成功退款按退款发生月份冲减，地区取订单收货地区快照，退款归原订单渠道。此处“净收入”是项目经营分析口径。</p><p>退款与订单先独立汇总后连接。成功退款可能来自更早月份的订单，不能只筛选当月下单记录。订单明细不直接参与订单金额求和。</p></section>
<section><h2>待验证的原因</h2><ul>{hypotheses}</ul><p>以上是后续调查方向，当前数据不能验证这些原因。</p></section>
<section><h2>可复现依据</h2><p>运行编号：{esc(result["run_id"])}<br>数据库 SHA256：{esc(result["provenance"]["database_sha256"])}<br>DB-GPT 提交：{esc(result["provenance"]["upstream_commit"])}</p><pre>{esc(json.dumps(result["params"], ensure_ascii=False, indent=2))}</pre>{attempts}<p>精确分数贡献、6 种替换顺序、查询结果、核验明细聚合和工作流轨迹见同目录 evidence.json。</p></section></main></html>"""


def save_result(result: dict, directory: Path = ARTIFACTS):
    folder = directory / result["run_id"]
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    if "analysis" in result:
        (folder / "report.html").write_text(render_report(result), encoding="utf-8")
        (folder / "query.sql").write_text(result["sql_attempts"][-1]["sql"], encoding="utf-8")
        (folder / "parameters.json").write_text(
            json.dumps(result["params"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return folder
