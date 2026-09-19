from __future__ import annotations

from .models import PerformanceResult, TechnicianPerformanceInput, WatchlistStatus

COMPLAINT_REVIEW_RATE = 0.03
REWORK_REVIEW_RATE = 0.03
QC_FAIL_REVIEW_RATE = 0.05


def _rate(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def calculate_performance(data: TechnicianPerformanceInput) -> PerformanceResult:
    """Mirror the approved Technician Tracker Combined Rate rule."""
    complaint_rate = _rate(data.technician_attributable_cases, data.completed_jobs)
    rework_rate = _rate(data.rework_cases, data.completed_jobs)
    qc_fail_rate = _rate(data.qc_fail_cases, data.completed_jobs)
    qc_coverage = _rate(data.qc_inspected_jobs, data.completed_jobs)

    reasons: list[str] = []
    if data.completed_jobs <= 0:
        reasons.append("ไม่มี Job Data ของช่างสำหรับใช้เป็นตัวหาร")
        return PerformanceResult(
            technician_id=data.technician_id,
            status=WatchlistStatus.INSUFFICIENT_DATA,
            risk_score=None,
            technician_issue_rate=complaint_rate,
            rework_rate=rework_rate,
            qc_fail_rate=qc_fail_rate,
            qc_coverage=qc_coverage,
            evidence_noncompliance_rate=None,
            reasons=tuple(reasons),
        )

    combined_rate = sum(rate or 0 for rate in (complaint_rate, rework_rate, qc_fail_rate))
    if data.completed_jobs < 50:
        reasons.append("จำนวนงานต่ำกว่า 50 งาน: rate-sensitive")

    if (
        (complaint_rate is not None and complaint_rate >= COMPLAINT_REVIEW_RATE)
        or (rework_rate is not None and rework_rate >= REWORK_REVIEW_RATE)
        or (qc_fail_rate is not None and qc_fail_rate >= QC_FAIL_REVIEW_RATE)
    ):
        status = WatchlistStatus.REVIEW
        reasons.append("มี Complaint หรือ Rework ตั้งแต่ 3% หรือ QC Fail ตั้งแต่ 5%")
    else:
        status = WatchlistStatus.NORMAL
        reasons.append("ทุกอัตรายังต่ำกว่าเกณฑ์ Review")

    return PerformanceResult(
        technician_id=data.technician_id,
        status=status,
        risk_score=round(combined_rate * 100, 2),
        technician_issue_rate=complaint_rate,
        rework_rate=rework_rate,
        qc_fail_rate=qc_fail_rate,
        qc_coverage=qc_coverage,
        evidence_noncompliance_rate=None,
        reasons=tuple(reasons),
    )
