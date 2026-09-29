import asyncio
import io
import json
import re
import zipfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response

from .config import load_model
from .data import ROOT, seed_database
from .report import ARTIFACTS, upstream_commit
from .workflow import AnalysisRequest, WorkflowFailure, run_analysis


@asynccontextmanager
async def lifespan(app):
    seed_database()
    yield


app = FastAPI(title="DB-GPT Commerce", lifespan=lifespan)
gate = asyncio.Semaphore(2)


@app.get("/")
def index():
    return FileResponse(ROOT / "commerce/static/index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "framework": "DB-GPT AWEL",
        "upstream_commit": upstream_commit(),
        "model": load_model().public(),
        "synthetic": True,
        "coverage": "2026-06 至 2026-08",
    }


@app.post("/api/analyze")
async def analyze(request: AnalysisRequest):
    async with gate:
        try:
            result = await run_analysis(request)
            result["report_url"] = f"/reports/{result['run_id']}/report.html"
            result["evidence_url"] = f"/reports/{result['run_id']}/evidence.json"
            result["download_url"] = f"/reports/{result['run_id']}/bundle.zip"
            return result
        except WorkflowFailure as exc:
            raise HTTPException(
                422,
                detail={
                    "message": str(exc),
                    "run_id": exc.run_id,
                    "evidence_url": f"/reports/{exc.run_id}/evidence.json",
                },
            ) from exc


@app.get("/api/runs")
def runs():
    if not ARTIFACTS.exists():
        return []
    results = []
    for p in sorted(ARTIFACTS.glob("*/evidence.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
        data = json.loads(p.read_text(encoding="utf-8"))
        results.append(
            {
                "run_id": data["run_id"],
                "status": data["status"],
                "mode": data["request"]["mode"],
                "created_at": data["provenance"]["generated_at"],
                "region": data["request"]["region"],
            }
        )
    return results


@app.get("/reports/{run_id}/{filename}")
def artifact(run_id: str, filename: str):
    if not re.fullmatch(r"[a-f0-9]{32}", run_id) or filename not in {
        "report.html",
        "evidence.json",
        "query.sql",
        "parameters.json",
        "bundle.zip",
    }:
        raise HTTPException(404)
    folder = ARTIFACTS / run_id
    if filename == "bundle.zip":
        if not (folder / "report.html").exists():
            raise HTTPException(404)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in ("report.html", "evidence.json", "query.sql", "parameters.json"):
                archive.write(folder / name, name)
        return Response(
            stream.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="commerce-{run_id[:8]}.zip"'},
        )
    path = folder / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)
