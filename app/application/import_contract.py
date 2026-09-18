from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook


def _key(value: object) -> str:
    return "".join(str(value or "").strip().casefold().split())


@dataclass(frozen=True)
class SheetContract:
    sheet_name: str
    required_columns: tuple[str, ...]
    accepted_aliases: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ImportValidation:
    sheet_name: str
    row_count: int
    missing_columns: tuple[str, ...]
    blank_key_rows: int

    @property
    def is_valid(self) -> bool:
        return not self.missing_columns and self.blank_key_rows == 0


CONTRACTS = (
    SheetContract(
        sheet_name="Job Data",
        required_columns=("job_no", "technician_id"),
        accepted_aliases={
            "job_no": ("Job No", "Job Number", "PO", "Order No"),
            "technician_id": ("Tech ID", "Technician ID"),
            "project": ("Project",),
            "vendor": ("LSP", "Vendor", "Sub Vendor"),
            "qc_result": ("QC Result", "QC"),
        },
    ),
    SheetContract(
        sheet_name="Complaint Log",
        required_columns=("job_no",),
        accepted_aliases={
            "job_no": ("Job No", "PO", "Order No"),
            "technician_id": ("Tech ID", "Technician ID"),
            "case_id": ("Case ID", "Complaint ID"),
            "rework": ("Rework",),
            "vendor": ("Vendor", "LSP", "Sub Vendor"),
        },
    ),
    SheetContract(
        sheet_name="Technician Master",
        required_columns=("technician_id",),
        accepted_aliases={
            "technician_id": ("Tech ID", "Technician ID"),
            "technician_name": ("Technician Name", "Name", "Tech Name"),
            "vendor": ("Vendor", "LSP", "Sub Vendor"),
        },
    ),
)


def _find_headers(headers: Iterable[object], contract: SheetContract) -> set[str]:
    normalised = {_key(header) for header in headers if header is not None}
    found: set[str] = set()
    for field, aliases in contract.accepted_aliases.items():
        if any(_key(alias) in normalised for alias in aliases):
            found.add(field)
    return found


def validate_workbook(path: str | Path) -> list[ImportValidation]:
    """Validate source structure only; it never assigns missing data or root cause."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    validations: list[ImportValidation] = []
    for contract in CONTRACTS:
        if contract.sheet_name not in workbook.sheetnames:
            validations.append(ImportValidation(contract.sheet_name, 0, contract.required_columns, 0))
            continue
        sheet = workbook[contract.sheet_name]
        header = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        found = _find_headers(header, contract)
        missing = tuple(field for field in contract.required_columns if field not in found)
        header_index = {_key(value): index for index, value in enumerate(header) if value is not None}
        key_aliases = contract.accepted_aliases[contract.required_columns[0]]
        key_index = next((header_index[_key(alias)] for alias in key_aliases if _key(alias) in header_index), None)
        rows = 0
        blank_key_rows = 0
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not any(value not in (None, "") for value in row):
                continue
            rows += 1
            if key_index is not None and (key_index >= len(row) or row[key_index] in (None, "")):
                blank_key_rows += 1
        validations.append(ImportValidation(contract.sheet_name, rows, missing, blank_key_rows))
    return validations

