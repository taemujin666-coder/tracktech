from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domain.models import PerformanceResult, TechnicianPerformanceInput
from app.domain.scoring import calculate_performance


@dataclass(frozen=True)
class TechnicianSnapshotSource:
    """Evidence-backed aggregates supplied by the read-model adapter.

    The calculation mirrors Performance Summary: job volume and QC Fail come
    from Job Data; Complaint and Rework come from verified Complaint Log cases.
    """

    technician_id: str
    vendor_name: str | None
    total_jobs: int
    completed_jobs: int
    complaint_cases: int
    rework_cases: int
    qc_inspected_jobs: int
    qc_fail_cases: int
    integrity_violations: int


@dataclass(frozen=True)
class TechnicianSnapshot:
    source: TechnicianSnapshotSource
    performance: PerformanceResult

    @property
    def volume_context(self) -> str:
        if self.source.total_jobs < 50:
            return "Low volume — rate-sensitive"
        if self.source.total_jobs < 100:
            return "Moderate volume"
        return "Higher volume"

    @property
    def status_reasons(self) -> tuple[str, ...]:
        context = (
            f"KPI ตาม Performance Summary: Complaint {self.source.complaint_cases}, "
            f"Rework {self.source.rework_cases} จาก Complaint Log; "
            f"QC Fail {self.source.qc_fail_cases} จาก Job Data; "
            f"Combined Rate {self.performance.risk_score or 0:.2f}%"
        )
        return (context, *self.performance.reasons)


def calculate_snapshots(sources: Iterable[TechnicianSnapshotSource]) -> list[TechnicianSnapshot]:
    """Calculate monitoring snapshots without inventing unavailable evidence."""
    snapshots: list[TechnicianSnapshot] = []
    for source in sources:
        performance = calculate_performance(
            TechnicianPerformanceInput(
                technician_id=source.technician_id,
                completed_jobs=source.total_jobs,
                technician_attributable_cases=source.complaint_cases,
                rework_cases=source.rework_cases,
                qc_inspected_jobs=source.qc_inspected_jobs,
                qc_fail_cases=source.qc_fail_cases,
            )
        )
        snapshots.append(TechnicianSnapshot(source, performance))
    return snapshots
