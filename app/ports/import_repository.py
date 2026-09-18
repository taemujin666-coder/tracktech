from __future__ import annotations

from typing import Protocol

from app.domain.import_models import ImportCommitResult, WorkbookPreview


class ImportRepository(Protocol):
    def commit(self, preview: WorkbookPreview, imported_by: str | None = None) -> ImportCommitResult: ...
