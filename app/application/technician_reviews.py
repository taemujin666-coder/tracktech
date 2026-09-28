from __future__ import annotations

from datetime import date


def followup_result(*, checklist_status: str, evidence_status: str,
                    qc_result: str, rework: bool | None,
                    same_issue: bool | None, evidence_reference: str | None) -> str:
    """Unknown outcomes stay open; only fully checked work can pass."""
    if (checklist_status == "COMPLETE" and evidence_status == "COMPLETE"
            and qc_result == "PASS" and rework is False and same_issue is False
            and (evidence_reference or "").strip()):
        return "PASS"
    return "FOLLOW_UP"


def can_close_review(followups: list[dict], target_jobs: int) -> bool:
    return (len(followups) >= target_jobs
            and len({row["job_no"] for row in followups}) == len(followups)
            and all(row["result"] == "PASS" for row in followups))


def evaluate_monitored_job(jobs: list[dict], investigation_date: date,
                           values: dict) -> tuple[date, str, str]:
    """Treat all product rows under an order as one monitored job."""
    if not jobs:
        raise ValueError("ไม่พบ Order No. ที่ยืนยัน Tech ID ตรงกับช่างรายนี้ใน Job Data")
    dates = {row["install_date"] for row in jobs if row["install_date"]}
    if len(dates) != 1 or next(iter(dates)) < investigation_date:
        raise ValueError("วันติดตั้งของงานติดตามต้องชัดเจนและไม่ก่อนวัน Investigation")
    outcomes = {(row["qc_result"] or "").strip().casefold() for row in jobs}
    completed = all((row["job_status"] or "").strip().casefold() == "completed" for row in jobs)
    qc_result = "FAIL" if "fail" in outcomes else "PASS" if completed and outcomes == {"pass"} else "PENDING"
    result = followup_result(
        checklist_status=values["checklist_status"], evidence_status=values["evidence_status"],
        qc_result=qc_result, rework=values["rework"], same_issue=values["same_issue"],
        evidence_reference=values["evidence_reference"])
    return next(iter(dates)), qc_result, result
