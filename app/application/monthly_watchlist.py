from __future__ import annotations


def classify_monthly_watchlist(
    *, jobs: int, affected_orders: int, complaints: int, rework: int, qc_fail: int
) -> dict:
    """Apply the August pilot's operational tiers to one technician's monthly counts."""
    if jobs < 0 or min(affected_orders, complaints, rework, qc_fail) < 0:
        raise ValueError("Monthly counts cannot be negative")

    combined_rate = (complaints + rework + qc_fail) / jobs if jobs else None
    if combined_rate is not None and combined_rate > 0.10:
        status = "CRITICAL"
        reason = "T3: Combined Rate มากกว่า 10% ของงานในเดือน"
    elif affected_orders >= 3:
        status = "WATCHLIST"
        reason = "T2: มี Order No. ที่ได้รับเรื่องอย่างน้อย 3 งานในเดือน"
    elif not jobs:
        status = "INSUFFICIENT_DATA"
        reason = "ไม่มีงานติดตั้งในเดือนนี้สำหรับคำนวณอัตรา"
    else:
        status = "NORMAL"
        reason = "ยังไม่ถึงเกณฑ์ T2 หรือ T3 ในเดือนนี้"

    return {"status": status, "combined_rate": combined_rate, "reason": reason}
