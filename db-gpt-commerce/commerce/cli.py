import argparse
import asyncio
import json
from pathlib import Path

from .data import DB_PATH, digest, seed_database
from .query import execute_readonly, validate_rows
from .workflow import AnalysisRequest, WorkflowFailure, run_analysis


def main():
    parser = argparse.ArgumentParser(description="DB-GPT 电商收入分析与证据复算")
    parser.add_argument("--mode", choices=["reference", "live"], default="reference")
    parser.add_argument("--as-of", default="2026-09-16")
    parser.add_argument("--region", choices=["华东", "华北"], default="华东")
    parser.add_argument(
        "--replay", type=Path, help="已有 evidence.json 路径；重执行 SQL 并核对原始结果与数据库指纹"
    )
    args = parser.parse_args()
    seed_database()
    if args.replay:
        result = json.loads(args.replay.read_text(encoding="utf-8"))
        if digest(DB_PATH) != result["provenance"]["database_sha256"]:
            raise SystemExit("数据库指纹不一致，不能复算同一快照")
        rows = execute_readonly(DB_PATH, result["sql_attempts"][-1]["sql"], result["params"])
        validate_rows(rows, result["independent_reference"])
        from .analysis import decompose

        if decompose(rows) != result["analysis"]:
            raise SystemExit("贡献分解与历史报告不一致")
        print("REPLAY VERIFIED: SQL、数据指纹与贡献分解一致")
        return
    request = AnalysisRequest(
        mode=args.mode,
        as_of=args.as_of,
        region=args.region,
        question=f"上个月{args.region}地区收入变化，分析订单量、客单价、退款和渠道结构的贡献，并输出计算依据。",
    )
    try:
        result = asyncio.run(run_analysis(request))
    except WorkflowFailure as exc:
        print(json.dumps({"status": "failed", "message": str(exc), "run_id": exc.run_id}, ensure_ascii=False))
        raise SystemExit(1)
    print(
        json.dumps(
            {
                "status": result["status"],
                "run_id": result["run_id"],
                "totals": result["analysis"]["totals"],
                "factors": result["analysis"]["factors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
