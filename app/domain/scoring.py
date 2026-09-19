from __future__ import annotations

from .models import PerformanceResult, TechnicianPerformanceInput, WatchlistStatus

MINIMUM_COMPLETED_JOBS = 20


def _rate(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def calculate_performance(data: TechnicianPerformanceInput) -> PerformanceResult:
    """Return an explainable pilot score.

    Missing QC or evidence data is represented as None and never converted to a
    favourable zero. The score is a monitoring aid, not a disciplinary decision.
    """
    issue_rate = _rate(data.technician_attributable_cases, data.completed_jobs)
    rework_rate = _rate(data.rework_cases, data.completed_jobs)
    qc_fail_rate = _rate(data.qc_fail_cases, data.qc_inspected_jobs)
    qc_coverage = _rate(data.qc_inspected_jobs, data.completed_jobs)
    evidence_rate = _rate(
        data.watchlist_jobs_missing_evidence,
        data.watchlist_jobs_requiring_evidence,
    )

    reasons: list[str] = []
    if data.completed_jobs < MINIMUM_COMPLETED_JOBS:
        reasons.append(f"มีงานปิดแล้ว {data.completed_jobs} งาน น้อยกว่าเกณฑ์ {MINIMUM_COMPLETED_JOBS} งาน")
        return PerformanceResult(
            technician_id=data.technician_id,
            status=WatchlistStatus.INSUFFICIENT_DATA,
            risk_score=None,
            technician_issue_rate=issue_rate,
            rework_rate=rework_rate,
            qc_fail_rate=qc_fail_rate,
            qc_coverage=qc_coverage,
            evidence_noncompliance_rate=evidence_rate,
            reasons=tuple(reasons),
        )

    if data.severe_case_count is not None and data.severe_case_count > 0:
        reasons.append("มีเคส Safety Property Damage หรือ Integrity ที่ต้อง Escalate ทันที")
        status = WatchlistStatus.ESCALATED
    else:
        # Normalise each pilot measure as a percentage. Unknown measures add no
        # score and are disclosed in reasons rather than assumed clean.
        components = [
            (issue_rate, 0.35, "Technician attributable issue"),
            (rework_rate, 0.25, "Rework"),
            (qc_fail_rate, 0.20, "QC fail"),
            (evidence_rate, 0.10, "Evidence ไม่ครบ"),
            (_rate(data.repeated_issue_cases, data.completed_jobs), 0.10, "Issue ซ้ำ"),
        ]
        score = sum(rate * weight * 100 for rate, weight, _ in components if rate is not None)
        missing = [name for rate, _, name in components if rate is None]
        if missing:
            reasons.append("ยังไม่มีข้อมูล: " + ", ".join(missing))
        if score >= 12 or data.repeated_issue_cases >= 2:
            status = WatchlistStatus.INVESTIGATE
            reasons.append("ความเสี่ยงสูงหรือพบเคสซ้ำ ต้องทบทวน Root Cause และ Action")
        elif score >= 5:
            status = WatchlistStatus.WATCHLIST
            reasons.append("ติดตามหลักฐานงานถัดไปและให้ Vendor Supervisor ตรวจ")
        else:
            status = WatchlistStatus.NORMAL
            reasons.append("อยู่ในเกณฑ์ติดตามปกติจากข้อมูลที่มี")
        return PerformanceResult(
            technician_id=data.technician_id,
            status=status,
            risk_score=round(score, 2),
            technician_issue_rate=issue_rate,
            rework_rate=rework_rate,
            qc_fail_rate=qc_fail_rate,
            qc_coverage=qc_coverage,
            evidence_noncompliance_rate=evidence_rate,
            reasons=tuple(reasons),
        )

    return PerformanceResult(
        technician_id=data.technician_id,
        status=status,
        risk_score=None,
        technician_issue_rate=issue_rate,
        rework_rate=rework_rate,
        qc_fail_rate=qc_fail_rate,
        qc_coverage=qc_coverage,
        evidence_noncompliance_rate=evidence_rate,
        reasons=tuple(reasons),
    )
