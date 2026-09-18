from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RootCauseCategory(StrEnum):
    TECHNICIAN = "TECHNICIAN"
    PRODUCT = "PRODUCT"
    SITE = "SITE"
    CUSTOMER = "CUSTOMER"
    PENDING_INVESTIGATION = "PENDING_INVESTIGATION"


class WatchlistStatus(StrEnum):
    NORMAL = "NORMAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    WATCHLIST = "WATCHLIST"
    INVESTIGATE = "INVESTIGATE"
    ESCALATED = "ESCALATED"


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class TechnicianPerformanceInput:
    technician_id: str
    completed_jobs: int
    technician_attributable_cases: int
    rework_cases: int
    qc_inspected_jobs: int
    qc_fail_cases: int
    watchlist_jobs_requiring_evidence: int
    watchlist_jobs_missing_evidence: int
    repeated_issue_cases: int
    severe_case_count: int = 0


@dataclass(frozen=True)
class PerformanceResult:
    technician_id: str
    status: WatchlistStatus
    risk_score: float | None
    technician_issue_rate: float | None
    rework_rate: float | None
    qc_fail_rate: float | None
    qc_coverage: float | None
    evidence_noncompliance_rate: float | None
    reasons: tuple[str, ...]

