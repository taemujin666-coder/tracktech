from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domain.models import PerformanceResult, TechnicianPerformanceInput
from app.domain.scoring import calculate_performance


@dataclass(frozen=True)
class TechnicianSnapshotSource:
    """Evidence-backed aggregates supplied by the read-model adapter.

    Historical-reference cases are accepted only when Complaint Log identifies a
    verified technician. They remain separate from Job Data matched cases so a
    reviewer can see that their order pre-dates the imported Job Data period.
    """

    technician_id: str
    vendor_name: str | None
    completed_jobs: int
    matched_cases: int
    historical_reference_cases: int
    rework_cases: int
    qc_inspected_jobs: int
    qc_fail_cases: int
    repeated_issue_cases: int


@dataclass(frozen=True)
class TechnicianSnapshot:
    source: TechnicianSnapshotSource
    performance: PerformanceResult

    @property
    def reported_complaint_cases(self) -> int:
        return self.source.matched_cases + self.source.historical_reference_cases

    @property
    def status_reasons(self) -> tuple[str, ...]:
        context = (
            f"Complaint ที่ยืนยัน Tech ได้ {self.reported_complaint_cases} เคส "
            f"(จับคู่ Job Data {self.source.matched_cases}, "
            f"อ้างอิงงานก่อนช่วง Job Data {self.source.historical_reference_cases})"
        )
        return (context, *self.performance.reasons)


def calculate_snapshots(sources: Iterable[TechnicianSnapshotSource]) -> list[TechnicianSnapshot]:
    """Calculate monitoring snapshots without inventing unavailable evidence."""
    snapshots: list[TechnicianSnapshot] = []
    for source in sources:
        performance = calculate_performance(
            TechnicianPerformanceInput(
                technician_id=source.technician_id,
                completed_jobs=source.completed_jobs,
                technician_attributable_cases=source.matched_cases + source.historical_reference_cases,
                rework_cases=source.rework_cases,
                qc_inspected_jobs=source.qc_inspected_jobs,
                qc_fail_cases=source.qc_fail_cases,
                # Evidence submission requirements and Safety/Integrity severity
                # are not yet imported, so they must remain unknown rather than 0.
                watchlist_jobs_requiring_evidence=None,
                watchlist_jobs_missing_evidence=None,
                repeated_issue_cases=source.repeated_issue_cases,
                severe_case_count=None,
            )
        )
        snapshots.append(TechnicianSnapshot(source, performance))
    return snapshots
