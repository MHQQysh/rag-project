import hashlib
import json
import random
import sqlite3
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "commerce.sqlite"
SEED = 20260916
SCHEMA = """
CREATE TABLE users(user_id INTEGER PRIMARY KEY, name TEXT NOT NULL, current_region TEXT NOT NULL);
CREATE TABLE channels(channel_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE products(product_id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL);
CREATE TABLE orders(
 order_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users,
 channel_id INTEGER NOT NULL REFERENCES channels, shipping_region TEXT NOT NULL,
 created_at TEXT NOT NULL, paid_at TEXT, status TEXT NOT NULL,
 listed_cents INTEGER NOT NULL CHECK(listed_cents>=0), paid_cents INTEGER NOT NULL CHECK(paid_cents>=0));
CREATE TABLE order_items(item_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders,
 product_id INTEGER NOT NULL REFERENCES products, quantity INTEGER NOT NULL CHECK(quantity>0),
 paid_cents INTEGER NOT NULL CHECK(paid_cents>=0));
CREATE TABLE refunds(refund_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders,
 refunded_at TEXT NOT NULL, status TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0));
CREATE INDEX orders_paid_region ON orders(paid_at,shipping_region);
CREATE INDEX refunds_time_status ON refunds(refunded_at,status);
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_database(path: Path = DB_PATH) -> Path:
    """Create once; never overwrite an existing database."""
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    with sqlite3.connect(path) as con:
        con.execute("PRAGMA foreign_keys=ON")
        con.executescript(SCHEMA)
        con.executemany("INSERT INTO channels VALUES (?,?)", [(1, "自营"), (2, "搜索广告"), (3, "直播")])
        con.executemany(
            "INSERT INTO users VALUES (?,?,?)",
            [(i, f"模拟用户{i:03d}", "华北" if i % 7 == 0 else "华东") for i in range(1, 201)],
        )
        con.executemany(
            "INSERT INTO products VALUES (?,?,?)",
            [(1, "基础款", "日用"), (2, "升级款", "日用"), (3, "配件", "配件")],
        )
        oid, iid = 0, 0
        grouped = {}
        profiles = {
            6: [(200, 30000), (200, 20000), (100, 10000)],
            7: [(600, 30000), (300, 20000), (100, 10000)],
            8: [(300, 28000), (300, 19000), (200, 9000)],
        }
        for month, entries in profiles.items():
            for region in ("华东", "华北"):
                for channel, (count, price) in enumerate(entries, 1):
                    count = count if region == "华东" else 40
                    ids = []
                    for j in range(count):
                        oid += 1
                        ids.append(oid)
                        paid = price + (500 if j % 2 else -500)
                        day = j % 27 + 1
                        paid_at = f"2026-{month:02d}-{day:02d}T12:00:00"
                        created_at = paid_at
                        if month == 8 and j == 0:
                            created_at = "2026-07-31T23:55:00"
                        con.execute(
                            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)",
                            (
                                oid,
                                rng.randint(1, 200),
                                channel,
                                region,
                                created_at,
                                paid_at,
                                "paid",
                                paid + 2000,
                                paid,
                            ),
                        )
                        # Two lines and repeated refunds intentionally expose join fan-out.
                        first = paid * 2 // 3
                        for value in (first, paid - first):
                            iid += 1
                            con.execute(
                                "INSERT INTO order_items VALUES (?,?,?,?,?)",
                                (iid, oid, rng.randint(1, 3), 1, value),
                            )
                    grouped[month, region, channel] = ids
        rid = 0
        for order in grouped[6, "华东", 1][:50]:
            rid += 1
            con.execute(
                "INSERT INTO refunds VALUES (?,?,?,?,?)",
                (rid, order, "2026-07-12T10:00:00", "success", 20000),
            )
        for order in grouped[7, "华东", 1][:100]:
            for day in (10, 18):
                rid += 1
                con.execute(
                    "INSERT INTO refunds VALUES (?,?,?,?,?)",
                    (rid, order, f"2026-08-{day}T10:00:00", "success", 9000),
                )
        for order in grouped[8, "华东", 1][:10]:
            rid += 1
            con.execute(
                "INSERT INTO refunds VALUES (?,?,?,?,?)", (rid, order, "2026-08-20T10:00:00", "failed", 5000)
            )
        for j in range(10):
            oid += 1
            con.execute(
                "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)",
                (oid, 1, 1, "华东", "2026-08-25T12:00:00", None, "cancelled", 50000, 0),
            )
    path.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "seed": SEED,
                "schema_version": 1,
                "coverage_start": "2026-06-01",
                "coverage_end_exclusive": "2026-09-01",
                "timezone": "Asia/Shanghai",
                "synthetic": True,
                "sha256": digest(path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def month_before(d: date) -> date:
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def periods(as_of: str) -> dict:
    end = date.fromisoformat(as_of).replace(day=1)
    current = month_before(end)
    previous = month_before(current)
    return {
        "previous_start": previous.isoformat(),
        "current_start": current.isoformat(),
        "end": end.isoformat(),
    }


def reference_rows(path: Path, params: dict) -> list[dict]:
    """Independent oracle: iterate raw rows, no SQL aggregation or analytical joins."""
    with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as con:
        channels = dict(con.execute("SELECT channel_id,name FROM channels"))
        orders = {
            r[0]: r
            for r in con.execute(
                "SELECT order_id,channel_id,shipping_region,paid_at,status,paid_cents FROM orders"
            )
        }
        refunds = list(con.execute("SELECT order_id,refunded_at,status,amount_cents FROM refunds"))
    result = []
    for label, start, end in (
        ("previous", params["previous_start"], params["current_start"]),
        ("current", params["current_start"], params["end"]),
    ):
        for cid, name in channels.items():
            count = paid = refund = 0
            for _, channel, region, at, status, amount in orders.values():
                if (
                    channel == cid
                    and region == params["region"]
                    and at
                    and start <= at < end
                    and status == "paid"
                ):
                    count += 1
                    paid += amount
            for oid, at, status, amount in refunds:
                order = orders[oid]
                if (
                    order[1] == cid
                    and order[2] == params["region"]
                    and status == "success"
                    and start <= at < end
                ):
                    refund += amount
            result.append(
                dict(period=label, channel=name, order_count=count, paid_cents=paid, refund_cents=refund)
            )
    return result
