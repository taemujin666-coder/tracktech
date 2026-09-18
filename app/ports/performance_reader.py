from __future__ import annotations

from typing import Protocol


class PerformanceReader(Protocol):
    def dashboard(self) -> dict: ...
    def technician_profile(self, technician_id: str) -> dict | None: ...

