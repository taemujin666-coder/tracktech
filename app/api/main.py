from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.application.demo_data import dashboard_demo
from app.application.import_contract import validate_workbook
from app.infrastructure.postgres_reader import PostgresPerformanceReader

APP_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = APP_ROOT / "static"
app = FastAPI(title="TrackTech", version="0.1.0")


def _reader_data() -> dict:
    if os.getenv("TRACKTECH_DEMO_MODE", "true").casefold() == "true":
        return dashboard_demo()
    return PostgresPerformanceReader().dashboard()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "tracktech", "mode": os.getenv("TRACKTECH_DEMO_MODE", "true")}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return _reader_data()


@app.get("/api/technicians/{technician_id}")
def technician_profile(technician_id: str) -> dict:
    data = _reader_data()
    if data["mode"] == "demo":
        match = next((item for item in data["technicians"] if item["technician_id"] == technician_id), None)
        if match:
            return match
    else:
        match = PostgresPerformanceReader().technician_profile(technician_id)
        if match:
            return match
    raise HTTPException(status_code=404, detail="Technician not found")


@app.post("/api/import/validate")
async def validate_import(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ .xlsx")
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temporary:
        shutil.copyfileobj(file.file, temporary)
        temporary_path = temporary.name
    try:
        validation = validate_workbook(temporary_path)
    finally:
        Path(temporary_path).unlink(missing_ok=True)
    return {
        "can_import": all(item.is_valid for item in validation),
        "sheets": [
            {
                "sheet_name": item.sheet_name,
                "row_count": item.row_count,
                "missing_columns": item.missing_columns,
                "blank_key_rows": item.blank_key_rows,
                "is_valid": item.is_valid,
            }
            for item in validation
        ],
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{asset_path:path}")
def static_asset(asset_path: str) -> FileResponse:
    asset = (STATIC_DIR / asset_path).resolve()
    if STATIC_DIR not in asset.parents or not asset.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(asset)

