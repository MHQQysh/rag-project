import asyncio
import json
import sqlite3
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from commerce.analysis import decompose
from commerce.data import SCHEMA, digest, periods, reference_rows, seed_database
from commerce.query import QueryRejected, STANDARD_SQL, execute_readonly, validate_rows
from commerce.workflow import AnalysisRequest, WorkflowFailure, run_analysis


@pytest.fixture
def db(tmp_path):
    return seed_database(tmp_path / "commerce.sqlite")


@pytest.fixture
def params():
    return {**periods("2026-09-16"), "region": "华东"}


def test_known_ground_truth(db, params):
    rows = execute_readonly(db, STANDARD_SQL, params)
    validate_rows(rows, reference_rows(db, params))
    result = decompose(rows)
    assert result["totals"]["previous"]["net_cents"] == 24_000_000
    assert result["totals"]["current"]["net_cents"] == 14_100_000
    assert result["delta_cents"] == -9_900_000
    assert result["change_pct"] == -41.25
    assert [f["cents"] for f in result["factors"]] == [-4_480_000, -3_277_500, -1_342_500, -800_000]


def test_deterministic_and_no_overwrite(tmp_path):
    a = seed_database(tmp_path / "a.sqlite")
    b = seed_database(tmp_path / "b.sqlite")
    assert digest(a) == digest(b)
    original = digest(a)
    seed_database(a)
    assert digest(a) == original


def test_month_boundaries_and_leap_year():
    assert periods("2026-01-31") == {
        "previous_start": "2025-11-01",
        "current_start": "2025-12-01",
        "end": "2026-01-01",
    }
    assert periods("2024-03-10")["current_start"] == "2024-02-01"
    with pytest.raises(ValueError):
        periods("2026-02-30")


def test_manual_dates_refunds_and_region(tmp_path, params):
    path = tmp_path / "tiny.sqlite"
    with sqlite3.connect(path) as con:
        con.executescript(SCHEMA)
        con.execute("INSERT INTO channels VALUES (1,'自营')")
        con.execute("INSERT INTO users VALUES (1,'某用户','华北')")
        orders = [
            (1, 1, 1, "华东", "2026-06-01", "2026-06-01", "paid", 10000, 10000),
            (2, 1, 1, "华东", "2026-07-31", "2026-08-01", "paid", 12000, 10000),
            (3, 1, 1, "华东", "2026-07-01", "2026-07-01", "paid", 20000, 20000),
            (4, 1, 1, "华东", "2026-08-01", None, "cancelled", 10000, 0),
            (5, 1, 1, "华东", "2026-09-01", "2026-09-01", "paid", 30000, 30000),
        ]
        con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)", orders)
        con.executemany(
            "INSERT INTO refunds VALUES (?,?,?,?,?)",
            [
                (1, 1, "2026-07-01", "success", 1000),
                (2, 3, "2026-08-01", "success", 2000),
                (3, 3, "2026-08-15", "success", 500),
                (4, 2, "2026-08-20", "failed", 5000),
                (5, 2, "2026-09-01", "success", 1000),
            ],
        )
    rows = execute_readonly(path, STANDARD_SQL, params)
    prev = next(r for r in rows if r["period"] == "previous")
    cur = next(r for r in rows if r["period"] == "current")
    assert (prev["order_count"], prev["paid_cents"], prev["refund_cents"]) == (1, 20000, 1000)
    assert (cur["order_count"], cur["paid_cents"], cur["refund_cents"]) == (1, 10000, 2500)
    validate_rows(rows, reference_rows(path, params))


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "SELECT 1; DROP TABLE orders",
        "PRAGMA table_info(orders)",
        "SELECT * FROM sqlite_master",
        "ATTACH DATABASE ':memory:' AS other",
        "SELECT load_extension('x')",
        "SELECT randomblob(1000000000)",
        "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT sum(x) FROM n",
        "SELECT order_id FROM orders",
    ],
)
def test_readonly_boundaries(db, params, sql):
    before = digest(db)
    with pytest.raises(QueryRejected):
        execute_readonly(db, sql, params)
    assert digest(db) == before


def test_fanout_is_rejected(db, params):
    bad = STANDARD_SQL.replace("FROM periods p JOIN orders o", "FROM periods p JOIN orders o").replace(
        "WHERE o.status = 'paid'", "JOIN order_items i ON i.order_id=o.order_id WHERE o.status = 'paid'"
    )
    with pytest.raises(QueryRejected, match="独立"):
        validate_rows(execute_readonly(db, bad, params), reference_rows(db, params))


def test_wrong_refund_month_and_duplicate_rows(db, params):
    wrong = STANDARD_SQL.replace("r.refunded_at", "o.paid_at")
    with pytest.raises(QueryRejected):
        validate_rows(execute_readonly(db, wrong, params), reference_rows(db, params))
    rows = reference_rows(db, params)
    rows[-1] = dict(rows[0])
    with pytest.raises(QueryRejected, match="重复"):
        validate_rows(rows, reference_rows(db, params))


def test_other_region_and_period(db):
    for as_of in ("2026-08-01", "2026-09-30"):
        params = {**periods(as_of), "region": "华北"}
        result = execute_readonly(db, STANDARD_SQL, params)
        validate_rows(result, reference_rows(db, params))
        assert all(r["refund_cents"] == 0 for r in result)


def test_shapley_missing_channel_and_symmetry():
    rows = [
        dict(period=p, channel=c, order_count=n, paid_cents=v, refund_cents=f)
        for p, c, n, v, f in [
            ("previous", "A", 2, 200, 0),
            ("previous", "B", 0, 0, 0),
            ("current", "A", 1, 150, 0),
            ("current", "B", 2, 200, 0),
        ]
    ]
    result = decompose(rows)
    assert result["delta_cents"] == 150
    assert sum(Fraction(f["exact_cents"]) for f in result["factors"]) == 150
    assert result["imputation_notes"]
    swapped = [{**r, "period": "previous" if r["period"] == "current" else "current"} for r in rows]
    reverse = decompose(swapped)
    assert [Fraction(f["exact_cents"]) for f in result["factors"]] == [
        -Fraction(f["exact_cents"]) for f in reverse["factors"]
    ]


def test_zero_period_rejected():
    rows = [
        dict(period=p, channel="A", order_count=0, paid_cents=0, refund_cents=0)
        for p in ("previous", "current")
    ]
    with pytest.raises(ValueError, match="不可识别"):
        decompose(rows)


def test_report_discloses_missing_channel(db, tmp_path):
    from commerce.report import render_report

    result = asyncio.run(run_analysis(AnalysisRequest(), db, tmp_path / "runs"))
    rows = [dict(r) for r in result["rows"]]
    for row in rows:
        if row["period"] == "previous" and row["channel"] == "直播":
            row.update(order_count=0, paid_cents=0, refund_cents=0)
    result["analysis"] = decompose(rows)
    report = render_report(result)
    assert "无订单" in report and "借用另一期间" in report and "—" in report


def test_real_awel_and_artifacts(db, tmp_path):
    result = asyncio.run(run_analysis(AnalysisRequest(), db, tmp_path / "runs"))
    folder = tmp_path / "runs" / result["run_id"]
    assert result["provenance"]["framework"] == "DB-GPT AWEL"
    assert len(result["trace"]) == 5
    assert result["status"] == "verified"
    assert (folder / "report.html").exists()
    assert (
        json.loads((folder / "evidence.json").read_text(encoding="utf-8"))["analysis"] == result["analysis"]
    )


@pytest.mark.parametrize(
    "analysis_request",
    [
        AnalysisRequest(as_of="2026-10-01"),
        AnalysisRequest(question="分析华北收入", region="华东"),
        AnalysisRequest(question="本月华东收入"),
        AnalysisRequest(question="分析商品销量"),
    ],
)
def test_out_of_scope_is_not_silently_answered(db, tmp_path, analysis_request):
    with pytest.raises(WorkflowFailure):
        asyncio.run(run_analysis(analysis_request, db, tmp_path / "runs"))
    evidence = list((tmp_path / "runs").glob("*/evidence.json"))
    assert len(evidence) == 1
    assert json.loads(evidence[0].read_text(encoding="utf-8"))["status"] == "failed"


def test_model_repair_path(db, tmp_path, monkeypatch):
    import commerce.workflow as workflow

    calls = []

    async def fake(state, error=""):
        calls.append(error)
        return "SELECT 1" if not error else STANDARD_SQL

    monkeypatch.setattr(workflow, "generate_sql", fake)
    result = asyncio.run(run_analysis(AnalysisRequest(mode="live"), db, tmp_path / "runs"))
    assert len(calls) == 2 and calls[1]
    assert [a["status"] for a in result["sql_attempts"]] == ["rejected", "verified"]


def test_model_failure_does_not_fallback(db, tmp_path, monkeypatch):
    import commerce.workflow as workflow

    async def fake(state, error=""):
        return "SELECT 1"

    monkeypatch.setattr(workflow, "generate_sql", fake)
    with pytest.raises(WorkflowFailure):
        asyncio.run(run_analysis(AnalysisRequest(mode="live"), db, tmp_path / "runs"))
    result = json.loads(next((tmp_path / "runs").glob("*/evidence.json")).read_text(encoding="utf-8"))
    assert "analysis" not in result and len(result["sql_attempts"]) == 2


def test_http_and_download(db, tmp_path, monkeypatch):
    import commerce.main as server

    async def local_run(request):
        return await run_analysis(request, db, tmp_path / "runs")

    monkeypatch.setattr(server, "run_analysis", local_run)
    monkeypatch.setattr(server, "ARTIFACTS", tmp_path / "runs")
    with TestClient(server.app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/api/health").json()["framework"] == "DB-GPT AWEL"
        response = client.post("/api/analyze", json={})
        assert response.status_code == 200
        result = response.json()
        assert client.get(result["report_url"]).status_code == 200
        assert client.get(result["download_url"]).content.startswith(b"PK")
        assert client.get("/reports/invalid/evidence.json").status_code == 404
        assert client.post("/api/analyze", json={"as_of": "2026-10-01"}).status_code == 422
        assert len(client.get("/api/runs").json()) == 2
