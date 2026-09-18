from __future__ import annotations

from app.domain.models import TechnicianPerformanceInput
from app.domain.scoring import calculate_performance


def dashboard_demo() -> dict:
    inputs = [
        TechnicianPerformanceInput("KSP43", 48, 4, 2, 39, 2, 4, 1, 1),
        TechnicianPerformanceInput("KSPUDON", 37, 1, 1, 0, 0, 3, 2, 0),
        TechnicianPerformanceInput("MVKSW05", 24, 0, 0, 22, 0, 0, 0, 0),
        TechnicianPerformanceInput("KSP17", 12, 2, 1, 10, 1, 0, 0, 0),
    ]
    results = [calculate_performance(item) for item in inputs]
    return {
        "mode": "demo",
        "summary": {
            "jobs": 12254,
            "complaint_cases": 206,
            "open_actions": 17,
            "pending_evidence": 6,
        },
        "technicians": [
            {
                "technician_id": result.technician_id,
                "vendor": "KSP" if result.technician_id.startswith("KSP") else "The Mall",
                "status": result.status,
                "risk_score": result.risk_score,
                "qc_coverage": result.qc_coverage,
                "reasons": result.reasons,
            }
            for result in results
        ],
    }

