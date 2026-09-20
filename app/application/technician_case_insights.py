from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Iterable, Mapping


TECHNICIAN_ROOT_CAUSES = {
    "work discipline",
    "technician defect",
    "individual judgment",
    "knowledge gap",
    "technician",
}
NON_TECHNICIAN_ROOT_CAUSES = {
    "product issue",
    "customer-related",
    "site constraint",
}
HUMAN_REVIEW_ROOT_CAUSES = {
    "rush / time pressure",
    "unclear standard",
    "other",
}

ACTION_LEVELS = {
    1: {
        "condition": "เกิดครั้งแรกหรือหลักฐานไม่ครบ",
        "measure": "Coaching และติดตามงานถัดไป",
    },
    2: {
        "condition": "ปัญหาเดิมเกิดซ้ำ",
        "measure": "Vendor Supervisor รับรองงานทุกครั้งในช่วงติดตาม",
    },
    3: {
        "condition": "เกิดซ้ำหลังทำ Corrective Action",
        "measure": "Investigate ร่วมกับ Vendor Manager และทีมช่าง",
    },
    4: {
        "condition": "ยังไม่ดีขึ้นหรือเกิดเคสรุนแรง",
        "measure": "ขอให้ Vendor เปลี่ยนทีม จำกัดประเภทงาน หรือพักทีมจากการรับงานนั้น",
    },
}


def _text(value: object) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _is_confirmed(value: object) -> bool:
    status = (_text(value) or "").casefold()
    return status in {"confirmed", "ยืนยันแล้ว"}


def _root_cause_classification(root_cause: str) -> str:
    normalised = root_cause.casefold()
    if normalised in TECHNICIAN_ROOT_CAUSES:
        return "TECHNICIAN"
    if normalised in NON_TECHNICIAN_ROOT_CAUSES:
        return "NON_TECHNICIAN"
    return "HUMAN_REVIEW"


def _ranked(rows: Iterable[Mapping[str, object]], field: str, *, confirmed_only: bool = False) -> list[dict]:
    counts: Counter[str] = Counter()
    labels: dict[str, str] = {}
    total = 0
    for row in rows:
        if confirmed_only and not _is_confirmed(row.get("root_cause_status")):
            continue
        label = _text(row.get(field))
        if not label:
            continue
        key = label.casefold()
        labels.setdefault(key, label)
        counts[key] += 1
        total += 1
    ranked = []
    for key, count in sorted(counts.items(), key=lambda item: (-item[1], labels[item[0]].casefold())):
        item = {
            "label": labels[key],
            "count": count,
            "share": round(count / total, 4) if total else 0,
        }
        if field == "root_cause_type":
            item["classification"] = _root_cause_classification(labels[key])
        ranked.append(item)
    return ranked


def _has_action(row: Mapping[str, object]) -> bool:
    return bool(_text(row.get("immediate_action")) or _text(row.get("preventive_action")))


def _action_level(cases: list[Mapping[str, object]]) -> dict:
    if not cases:
        return {
            "level": None,
            "condition": "ยังไม่มีเคสที่ผูกกับช่าง",
            "measure": "ติดตามตามปกติ",
            "reason": "ไม่มีหลักฐานเคสสำหรับกำหนด Action Level",
            "attributable_cases": 0,
            "post_action_repeats": 0,
        }

    attributable = [
        row
        for row in cases
        if _is_confirmed(row.get("root_cause_status"))
        and (_text(row.get("root_cause_type")) or "").casefold() in TECHNICIAN_ROOT_CAUSES
    ]
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    labels: dict[str, str] = {}
    for row in attributable:
        category = _text(row.get("issue_category"))
        if not category:
            continue
        key = category.casefold()
        labels.setdefault(key, category)
        grouped[key].append(row)

    repeat_key = max(grouped, key=lambda key: len(grouped[key]), default=None)
    repeat_count = len(grouped[repeat_key]) if repeat_key else 0
    post_action_repeats = 0
    for rows in grouped.values():
        rows = sorted(rows, key=lambda row: _date(row.get("complaint_date")) or date.min)
        action_dates: list[date] = []
        for row in rows:
            complaint_date = _date(row.get("complaint_date"))
            if complaint_date and any(action_date < complaint_date for action_date in action_dates):
                post_action_repeats += 1
            if _has_action(row):
                action_date = _date(row.get("close_date")) or complaint_date
                if action_date:
                    action_dates.append(action_date)

    severe_cases = sum(
        any(token in (_text(row.get("case_status")) or "").casefold() for token in ("escalated", "critical", "severe", "รุนแรง"))
        for row in attributable
    )

    if severe_cases or post_action_repeats >= 2:
        level = 4
        reason = (
            f"พบเคสที่มีสถานะรุนแรงหรือถูกยกระดับ {severe_cases} เคส"
            if severe_cases
            else f"พบปัญหาเดิมเกิดซ้ำหลังมี Action {post_action_repeats} ครั้ง"
        )
    elif post_action_repeats == 1:
        level = 3
        reason = "พบปัญหาเดิมเกิดซ้ำหลังมีการบันทึก Corrective Action 1 ครั้ง"
    elif repeat_count >= 2 and repeat_key:
        level = 2
        reason = f"Issue “{labels[repeat_key]}” เกิดซ้ำ {repeat_count} เคสที่ยืนยันสาเหตุจากช่าง"
    else:
        level = 1
        reason = (
            "ยังไม่มีเคสที่ยืนยันสาเหตุจากช่างครบถ้วน จึงใช้มาตรการขั้นต่ำและติดตามหลักฐาน"
            if cases and not attributable
            else "ยังไม่พบปัญหาเดิมเกิดซ้ำหลังยืนยัน Root Cause"
        )

    return {
        "level": level,
        **ACTION_LEVELS[level],
        "reason": reason,
        "attributable_cases": len(attributable),
        "post_action_repeats": post_action_repeats,
    }


def build_technician_case_insights(cases: Iterable[Mapping[str, object]]) -> dict:
    rows = list(cases)
    issue_categories = _ranked(rows, "issue_category")
    root_causes = _ranked(rows, "root_cause_type", confirmed_only=True)
    confirmed_root_causes = sum(_is_confirmed(row.get("root_cause_status")) for row in rows)
    return {
        "distinct_issue_categories": len(issue_categories),
        "issue_categories": issue_categories,
        "dominant_issue": issue_categories[0] if issue_categories else None,
        "confirmed_root_cause_cases": confirmed_root_causes,
        "pending_root_cause_cases": len(rows) - confirmed_root_causes,
        "root_causes": root_causes,
        "dominant_root_cause": root_causes[0] if root_causes else None,
        "action_level": _action_level(rows),
    }
