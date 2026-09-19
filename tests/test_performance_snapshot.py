import unittest

from app.application.performance_snapshot import TechnicianSnapshotSource, calculate_snapshots
from app.domain.models import WatchlistStatus


class PerformanceSnapshotTest(unittest.TestCase):
    def test_historical_complaint_is_attributed_with_its_own_provenance(self):
        source = TechnicianSnapshotSource(
            technician_id="T001",
            vendor_name="Vendor",
            completed_jobs=25,
            matched_cases=1,
            historical_reference_cases=2,
            rework_cases=1,
            qc_inspected_jobs=24,
            qc_fail_cases=1,
            repeated_issue_cases=0,
        )

        snapshot = calculate_snapshots([source])[0]

        self.assertEqual(snapshot.reported_complaint_cases, 3)
        self.assertIn("อ้างอิงงานก่อนช่วง Job Data 2", snapshot.status_reasons[0])
        self.assertNotEqual(snapshot.performance.status, WatchlistStatus.INSUFFICIENT_DATA)

    def test_unknown_evidence_requirements_are_not_silently_scored_as_zero(self):
        source = TechnicianSnapshotSource(
            technician_id="T002",
            vendor_name="Vendor",
            completed_jobs=25,
            matched_cases=0,
            historical_reference_cases=0,
            rework_cases=0,
            qc_inspected_jobs=0,
            qc_fail_cases=0,
            repeated_issue_cases=0,
        )

        snapshot = calculate_snapshots([source])[0]

        self.assertIn("Evidence ไม่ครบ", " ".join(snapshot.performance.reasons))
        self.assertIn("QC fail", " ".join(snapshot.performance.reasons))


if __name__ == "__main__":
    unittest.main()
