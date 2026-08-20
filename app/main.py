from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .filesystem import browse, default_root, resolve_allowed
from .models import JobCreate
from .runner import create_job, get_job, list_jobs, preview_commands

app = FastAPI(title="vcsi-web", version="0.1.0")
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/config")
def config() -> dict:
    return {
        "input_roots": [str(p) for p in settings.input_roots],
        "output_roots": [str(p) for p in settings.output_roots],
    }


@app.get("/api/browse")
def api_browse(kind: str = Query(pattern="^(input|output)$"), path: str | None = None) -> dict:
    roots = settings.input_roots if kind == "input" else settings.output_roots
    try:
        target = resolve_allowed(path, roots) if path else default_root(roots)
        return browse(target, roots, videos_only=(kind == "input"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/preview")
def api_preview(payload: JobCreate) -> dict:
    try:
        return {"commands": preview_commands(payload)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs", status_code=202)
def api_create_job(payload: JobCreate) -> dict:
    try:
        return create_job(payload).public()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/jobs")
def api_list_jobs() -> list[dict]:
    return list_jobs()


@app.get("/api/jobs/{job_id}")
def api_get_job(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.public()


@app.get("/api/output")
def api_output(path: str) -> FileResponse:
    try:
        file_path = resolve_allowed(path, settings.output_roots)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(file_path)
