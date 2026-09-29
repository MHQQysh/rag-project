from fractions import Fraction
from itertools import permutations


def decompose(rows: list[dict]) -> dict:
    groups = {p: {r["channel"]: r for r in rows if r["period"] == p} for p in ("previous", "current")}
    channels = sorted(set(groups["previous"]) | set(groups["current"]))
    totals = {}
    for p, group in groups.items():
        count = sum(r["order_count"] for r in group.values())
        paid = sum(r["paid_cents"] for r in group.values())
        refund = sum(r["refund_cents"] for r in group.values())
        totals[p] = {
            "order_count": count,
            "paid_cents": paid,
            "refund_cents": refund,
            "net_cents": paid - refund,
            "aov_cents": float(Fraction(paid, count)) if count else None,
        }
    if not all(t["order_count"] for t in totals.values()):
        raise ValueError("任一整月没有支付订单时，渠道结构与客单价分解不可识别；请更换时间或地区")
    values = []
    imputed = []
    for p, other in (("previous", "current"), ("current", "previous")):
        n = totals[p]["order_count"]
        shares = []
        prices = []
        for channel in channels:
            r = groups[p][channel]
            alt = groups[other][channel]
            shares.append(Fraction(r["order_count"], n))
            if r["order_count"]:
                prices.append(Fraction(r["paid_cents"], r["order_count"]))
            else:
                prices.append(
                    Fraction(alt["paid_cents"], alt["order_count"]) if alt["order_count"] else Fraction(0)
                )
                imputed.append(f"{p}/{channel} 无订单，客单价借用另一期间；两期均无订单取零")
        values.append([n, shares, prices])

    def gross(v):
        return v[0] * sum(s * a for s, a in zip(v[1], v[2]))

    contribution = [Fraction(0)] * 3
    permutations_evidence = []
    for permutation in permutations(range(3)):
        state = list(values[0])
        before = gross(state)
        steps = []
        for idx in permutation:
            state[idx] = values[1][idx]
            after = gross(state)
            contribution[idx] += (after - before) / 6
            steps.append({"factor": idx, "marginal_cents_exact": str(after - before)})
            before = after
        permutations_evidence.append(steps)
    contribution.append(Fraction(totals["previous"]["refund_cents"] - totals["current"]["refund_cents"]))
    delta = totals["current"]["net_cents"] - totals["previous"]["net_cents"]
    assert sum(contribution) == delta
    labels = ["订单量", "渠道结构", "渠道内客单价", "退款变化"]
    factors = [
        {
            "name": name,
            "cents": float(value),
            "exact_cents": str(value),
            "share_of_change_pct": float(value / delta * 100) if delta else None,
        }
        for name, value in zip(labels, contribution)
    ]
    table = []
    for channel in channels:
        item = {"channel": channel}
        for p in groups:
            r = groups[p][channel]
            item[p] = {
                **r,
                "share_pct": r["order_count"] / totals[p]["order_count"] * 100,
                "aov_cents": r["paid_cents"] / r["order_count"] if r["order_count"] else None,
                "net_cents": r["paid_cents"] - r["refund_cents"],
            }
        table.append(item)
    return {
        "totals": totals,
        "delta_cents": delta,
        "change_pct": delta / totals["previous"]["net_cents"] * 100
        if totals["previous"]["net_cents"]
        else None,
        "factors": factors,
        "channels": table,
        "reconciliation_cents": float(sum(contribution) - delta),
        "formula": "净收入 = N × Σ(渠道订单占比 s_c × 渠道内实付客单价 a_c) − 当月成功退款；N/s/a 的贡献取 6 种替换顺序的平均边际差。",
        "permutations": permutations_evidence,
        "imputation_notes": imputed,
        "interpretation": "贡献是指标恒等式的算术分解，不是因果结论。总体客单价变化已分配至渠道结构与渠道内客单价，不能重复相加。",
        "hypotheses": [
            "流量下降是否导致订单减少：需补充曝光、访问量和转化率。",
            "促销或商品组合是否影响客单价：需补充折扣活动及商品结构对照。",
            "退款增长是否来自质量或履约问题：需补充退款原因及物流证据。",
        ],
    }
