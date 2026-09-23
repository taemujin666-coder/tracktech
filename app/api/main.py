from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from zipfile import BadZipFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from openpyxl.utils.exceptions import InvalidFileException

from app.application.technician_case_insights import build_technician_case_insights
from app.application.demo_data import dashboard_demo
from app.application.import_contract import validate_workbook
from app.application.workbook_import import preview_workbook
from app.infrastructure.postgres_import_repository import PostgresImportRepository
from app.infrastructure.postgres_reader import PostgresPerformanceReader

APP_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = APP_ROOT / "static"
app = FastAPI(title="TrackTech", version="0.1.0")
MAX_WORKBOOK_BYTES = 30 * 1024 * 1024


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


@app.get("/api/watchlist")
def monthly_watchlist(month: str = "2026-08") -> dict:
    try:
        starts_on = date.fromisoformat(f"{month}-01")
        if starts_on.strftime("%Y-%m") != month:
            raise ValueError("Invalid month")
    except ValueError as error:
        raise HTTPException(status_code=422, detail="ระบุเดือนในรูปแบบ YYYY-MM") from error

    if os.getenv("TRACKTECH_DEMO_MODE", "true").casefold() == "true":
        return {"mode": "demo", "month": month, "technicians": []}
    return PostgresPerformanceReader().monthly_watchlist(starts_on)


@app.get("/api/technicians/{technician_id}")
def technician_profile(technician_id: str) -> dict:
    data = _reader_data()
    if data["mode"] == "demo":
        match = next((item for item in data["technicians"] if item["technician_id"] == technician_id), None)
        if match:
            return {
                "mode": "demo",
                "profile": {
                    **match,
                    "technician_name": None,
                    "team": "ทีมตัวอย่าง",
                    "vendor_name": match.get("vendor"),
                    "area": None,
                    "active": True,
                    "total_jobs": None,
                    "complaint_cases": None,
                    "rework_cases": None,
                    "qc_fail_cases": None,
                    "complaint_rate": None,
                    "rework_rate": None,
                    "qc_fail_rate": None,
                    "combined_rate": None,
                    "service_mind_cases": 0,
                    "volume_context": "ข้อมูลตัวอย่าง",
                },
                "case_insights": build_technician_case_insights([]),
                "history_summary": {"job_records": 0, "case_records": 0, "review_cases": 0},
                "jobs": [],
                "cases": [],
                "review_cases": [],
            }
    else:
        match = PostgresPerformanceReader().technician_profile(technician_id)
        if match:
            return {"mode": "live", **match}
    raise HTTPException(status_code=404, detail="Technician not found")


@contextmanager
def _uploaded_workbook(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ .xlsx")
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temporary:
        total = 0
        while chunk := file.file.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_WORKBOOK_BYTES:
                Path(temporary.name).unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="ไฟล์ใหญ่เกิน 30 MB")
            temporary.write(chunk)
        temporary_path = temporary.name
    try:
        yield Path(temporary_path)
    finally:
        Path(temporary_path).unlink(missing_ok=True)


@app.post("/api/import/validate")
async def validate_import(file: UploadFile = File(...)) -> dict:
    """Backwards-compatible structure validation endpoint."""
    with _uploaded_workbook(file) as temporary_path:
        validation = validate_workbook(temporary_path)
    return {
        "can_import": all(item.is_valid for item in validation),
        "sheets": [
            {
                "sheet_name": item.sheet_name,
                "header_row": item.header_row,
                "row_count": item.row_count,
                "missing_columns": item.missing_columns,
                "blank_key_rows": item.blank_key_rows,
                "is_valid": item.is_valid,
            }
            for item in validation
        ],
    }


@app.post("/api/import/preview")
async def preview_import(file: UploadFile = File(...)) -> dict:
    try:
        with _uploaded_workbook(file) as temporary_path:
            preview = preview_workbook(temporary_path, file.filename)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (OSError, KeyError, BadZipFile, InvalidFileException) as error:
        raise HTTPException(status_code=400, detail="อ่านไฟล์ Excel ไม่สำเร็จ กรุณาตรวจว่าไฟล์ไม่เสียหาย") from error
    return {"can_import": True, **preview.public_dict()}


@app.post("/api/import/commit")
async def commit_import(file: UploadFile = File(...)) -> dict:
    if os.getenv("TRACKTECH_DEMO_MODE", "true").casefold() == "true":
        raise HTTPException(
            status_code=409,
            detail="ตอนนี้เป็นโหมดตัวอย่าง: Preview ได้ แต่ต้องตั้งฐานข้อมูลและ TRACKTECH_DEMO_MODE=false ก่อนบันทึกจริง",
        )
    try:
        with _uploaded_workbook(file) as temporary_path:
            preview = preview_workbook(temporary_path, file.filename)
            result = PostgresImportRepository().commit(preview)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "committed", **result.as_dict()}


@app.post("/api/performance/refresh")
def refresh_performance_snapshot() -> dict:
    if os.getenv("TRACKTECH_DEMO_MODE", "true").casefold() == "true":
        raise HTTPException(status_code=409, detail="โหมดตัวอย่างยังไม่มีข้อมูลจริงสำหรับสร้าง Performance Snapshot")
    return {"status": "refreshed", **PostgresPerformanceReader().refresh_snapshot()}


@app.get("/api/reconciliation")
def reconciliation_queue() -> dict:
    if os.getenv("TRACKTECH_DEMO_MODE", "true").casefold() == "true":
        raise HTTPException(status_code=409, detail="โหมดตัวอย่างยังไม่มีคิวตรวจสอบจากข้อมูลจริง")
    return PostgresPerformanceReader().reconciliation_queue()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{asset_path:path}")
def static_asset(asset_path: str) -> FileResponse:
    asset = (STATIC_DIR / asset_path).resolve()
    if STATIC_DIR not in asset.parents or not asset.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(asset)
