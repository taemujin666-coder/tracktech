import unittest
from datetime import date

from app.application.technician_case_insights import build_technician_case_insights


def case(
    complaint_date: date,
    *,
    issue: str = "Workmanship",
    root_cause: str = "Work discipline",
    root_cause_status: str = "Confirmed",
    action: str | None = None,
    close_date: date | None = None,
    case_status: str = "Resolved",
):
    return {
        "complaint_date": complaint_date,
        "issue_category": issue,
        "root_cause_type": root_cause,
        "root_cause_status": root_cause_status,
        "immediate_action": action,
        "preventive_action": None,
        "close_date": close_date,
        "case_status": case_status,
    }


class TechnicianCaseInsightsTest(unittest.TestCase):
    def test_no_cases_does_not_invent_an_action_level(self):
        insights = build_technician_case_insights([])
        self.assertIsNone(insights["action_level"]["level"])

    def test_ranks_issue_and_confirmed_root_cause_distributions(self):
        insights = build_technician_case_insights(
            [
                case(date(2026, 1, 1)),
                case(date(2026, 1, 2)),
                case(date(2026, 1, 3), issue="Communication / Service", root_cause="Site constraint"),
            ]
        )
        self.assertEqual(insights["distinct_issue_categories"], 2)
        self.assertEqual(insights["dominant_issue"]["label"], "Workmanship")
        self.assertEqual(insights["dominant_issue"]["count"], 2)
        self.assertEqual(insights["dominant_root_cause"]["label"], "Work discipline")
        self.assertEqual(insights["dominant_root_cause"]["classification"], "TECHNICIAN")

    def test_repeated_confirmed_technician_issue_is_level_two(self):
        insights = build_technician_case_insights(
            [case(date(2026, 1, 1)), case(date(2026, 2, 1))]
        )
        self.assertEqual(insights["action_level"]["level"], 2)

    def test_repeat_after_corrective_action_is_level_three(self):
        insights = build_technician_case_insights(
            [
                case(date(2026, 1, 1), action="Coaching", close_date=date(2026, 1, 5)),
                case(date(2026, 2, 1)),
            ]
        )
        self.assertEqual(insights["action_level"]["level"], 3)

    def test_persistent_repeat_after_action_is_level_four(self):
        insights = build_technician_case_insights(
            [
                case(date(2026, 1, 1), action="Coaching", close_date=date(2026, 1, 5)),
                case(date(2026, 2, 1)),
                case(date(2026, 3, 1)),
            ]
        )
        self.assertEqual(insights["action_level"]["level"], 4)

    def test_non_technician_or_unconfirmed_causes_do_not_escalate(self):
        insights = build_technician_case_insights(
            [
                case(date(2026, 1, 1), root_cause="Product issue"),
                case(date(2026, 2, 1), root_cause="Product issue"),
                case(date(2026, 3, 1), root_cause="Work discipline", root_cause_status="Pending Investigation"),
            ]
        )
        self.assertEqual(insights["action_level"]["level"], 1)
        self.assertEqual(insights["action_level"]["attributable_cases"], 0)


if __name__ == "__main__":
    unittest.main()
