import math
import sqlite3
import time
from pathlib import Path

import sqlparse

STANDARD_SQL = """WITH periods(period, start_at, end_at) AS (
 SELECT 'previous', :previous_start, :current_start
 UNION ALL SELECT 'current', :current_start, :end
), payments AS (
 SELECT p.period, o.channel_id, COUNT(*) AS order_count, SUM(o.paid_cents) AS paid_cents
 FROM periods p JOIN orders o ON o.paid_at >= p.start_at AND o.paid_at < p.end_at
 WHERE o.status = 'paid' AND o.shipping_region = :region
 GROUP BY p.period, o.channel_id
), successful_refunds AS (
 SELECT p.period, o.channel_id, SUM(r.amount_cents) AS refund_cents
 FROM periods p JOIN refunds r ON r.refunded_at >= p.start_at AND r.refunded_at < p.end_at
 JOIN orders o ON o.order_id = r.order_id
 WHERE r.status = 'success' AND o.shipping_region = :region
 GROUP BY p.period, o.channel_id
)
SELECT p.period, c.name AS channel, COALESCE(a.order_count,0) AS order_count,
 COALESCE(a.paid_cents,0) AS paid_cents, COALESCE(r.refund_cents,0) AS refund_cents
FROM periods p CROSS JOIN channels c
LEFT JOIN payments a ON a.period=p.period AND a.channel_id=c.channel_id
LEFT JOIN successful_refunds r ON r.period=p.period AND r.channel_id=c.channel_id
ORDER BY p.period,c.channel_id"""

TABLES = {"orders", "order_items", "products", "users", "refunds", "channels"}
FUNCTIONS = {
    "count",
    "sum",
    "avg",
    "min",
    "max",
    "coalesce",
    "ifnull",
    "nullif",
    "round",
    "abs",
    "substr",
    "substring",
    "strftime",
    "date",
    "datetime",
    "cast",
    "lower",
    "upper",
    "length",
    "total",
}


class QueryRejected(ValueError):
    pass


def execute_readonly(path: Path, sql: str, params: dict, *, budget_seconds=3.0) -> list[dict]:
    if len(sql) > 20000 or len(sqlparse.split(sql)) != 1:
        raise QueryRejected("只允许一条长度不超过 20000 字符的查询")
    statement = sqlparse.parse(sql)[0]
    if statement.get_type() != "SELECT":
        raise QueryRejected("只允许 SELECT 或 WITH ... SELECT")
    con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    began = time.monotonic()
    steps = 0

    def progress():
        nonlocal steps
        steps += 1000
        return int(steps > 2_000_000 or time.monotonic() - began > budget_seconds)

    def authorize(action, arg1, arg2, db, source):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ and arg1 in TABLES:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    con.set_authorizer(authorize)
    con.set_progress_handler(progress, 1000)
    try:
        cur = con.execute(sql, params)
        names = [c[0] for c in cur.description]
        if len(names) != len(set(names)):
            raise QueryRejected("查询列名重复")
        rows = cur.fetchmany(101)
        if len(rows) > 100:
            raise QueryRejected("查询结果超过 100 行")
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        raise QueryRejected(f"查询被拒绝或执行失败：{exc}") from exc
    finally:
        con.close()


def validate_rows(actual: list[dict], expected: list[dict]) -> None:
    columns = {"period", "channel", "order_count", "paid_cents", "refund_cents"}
    if len(actual) != len(expected):
        raise QueryRejected("结果必须包含两个期间的全部渠道（包括零值渠道）")
    seen = set()
    normalized = []
    for row in actual:
        if set(row) != columns:
            raise QueryRejected("输出列必须为 period/channel/order_count/paid_cents/refund_cents")
        key = (row["period"], row["channel"])
        if key in seen:
            raise QueryRejected("期间渠道重复，可能存在连接扇出")
        seen.add(key)
        r = dict(row)
        for name in ("order_count", "paid_cents", "refund_cents"):
            value = r[name]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
                or int(value) != value
            ):
                raise QueryRejected("计数和金额必须为非负整数，金额单位是分")
            r[name] = int(value)
        normalized.append(r)
    order = lambda r: (r["period"], r["channel"])
    if sorted(normalized, key=order) != sorted(expected, key=order):
        raise QueryRejected("与独立订单/退款明细核验不一致；检查支付时间、成功退款发生月、地区快照及重复连接")
