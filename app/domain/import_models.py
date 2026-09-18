from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import StrEnum


class TechnicianIdentityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    MISSING_TECHNICIAN_ID = "MISSING_TECHNICIAN_ID"
    UNVERIFIED_TECHNICIAN_IDENTITY = "UNVERIFIED_TECHNICIAN_IDENTITY"
    PENDING_MASTER_MATCH = "PENDING_MASTER_MATCH"


class CaseLinkStatus(StrEnum):
    MATCHED = "MATCHED"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    TECHNICIAN_CONFLICT = "TECHNICIAN_CONFLICT"


class QCEvidenceStatus(StrEnum):
    RECORDED = "RECORDED"
    NOT_APPLICABLE_NOT_COMPLETE = "NOT_APPLICABLE_NOT_COMPLETE"
    NOT_APPLICABLE_CANCELLED = "NOT_APPLICABLE_CANCELLED"
    MISSING_SOURCE_VALUE = "MISSING_SOURCE_VALUE"


@dataclass(frozen=True)
class TechnicianRecord:
    technician_id: str
    technician_name: str | None
    team: str | None
    vendor_name: str | None
    source_status: str | None
    area: str | None


@dataclass(frozen=True)
class JobRecord:
    source_job_key: str
    source_row_number: int
    job_no: str
    install_date: date | None
    product_model: str | None
    source_tech_code: str | None
    technician_id: str | None
    technician_identity_status: TechnicianIdentityStatus
    project_name: str | None
    vendor_name: str | None
    qc_date: date | None
    qc_result: str | None
    qc_evidence_status: QCEvidenceStatus
    job_status: str | None
    record_hash: str


@dataclass(frozen=True)
class CaseRecord:
    source_case_key: str
    source_row_number: int
    job_no: str
    completed_date: date | None
    complaint_date: date | None
    source_tech_code: str | None
    technician_id: str | None
    technician_identity_status: TechnicianIdentityStatus
    issue_category: str | None
    issue_detail: str | None
    qc_result: str | None
    root_cause_status: str | None
    root_cause_type: str | None
    root_cause_detail: str | None
    immediate_action: str | None
    preventive_action: str | None
    rework: bool | None
    service_mind: bool | None
    owner_name: str | None
    case_status: str | None
    close_date: date | None
    link_status: CaseLinkStatus
    record_hash: str


@dataclass
class WorkbookPreview:
    filename: str
    content_hash: str
    technicians: list[TechnicianRecord] = field(default_factory=list)
    jobs: list[JobRecord] = field(default_factory=list)
    cases: list[CaseRecord] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def public_dict(self) -> dict:
        return {"filename": self.filename, "content_hash": self.content_hash, "summary": self.summary, "warnings": self.warnings}


@dataclass(frozen=True)
class ImportCommitResult:
    import_run_id: str
    technicians_inserted: int
    technicians_updated: int
    technicians_unchanged: int
    jobs_inserted: int
    jobs_updated: int
    jobs_unchanged: int
    cases_inserted: int
    cases_updated: int
    cases_unchanged: int
    conflicts: int

    def as_dict(self) -> dict:
        return asdict(self)
