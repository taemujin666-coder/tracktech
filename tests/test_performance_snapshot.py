import unittest

from app.application.performance_snapshot import TechnicianSnapshotSource, calculate_snapshots
from app.domain.models import WatchlistStatus


class PerformanceSnapshotTest(unittest.TestCase):
    def test_discloses_the_approved_performance_summary_sources(self):
        source = TechnicianSnapshotSource(
            technician_id="T001",
            vendor_name="Vendor",
            total_jobs=100,
            completed_jobs=96,
            complaint_cases=2,
            rework_cases=3,
            qc_inspected_jobs=98,
            qc_fail_cases=1,
            integrity_violations=4,
        )

        snapshot = calculate_snapshots([source])[0]

        self.assertEqual(snapshot.performance.status, WatchlistStatus.REVIEW)
        self.assertEqual(snapshot.performance.risk_score, 6.0)
        self.assertEqual(snapshot.volume_context, "Higher volume")
        self.assertIn("KPI ตาม Performance Summary", snapshot.status_reasons[0])
        self.assertIn("Complaint Log", snapshot.status_reasons[0])
        self.assertIn("Job Data", snapshot.status_reasons[0])

    def test_low_volume_context_is_disclosed_without_excluding_the_technician(self):
        source = TechnicianSnapshotSource(
            technician_id="T002",
            vendor_name="Vendor",
            total_jobs=32,
            completed_jobs=30,
            complaint_cases=0,
            rework_cases=0,
            qc_inspected_jobs=31,
            qc_fail_cases=0,
            integrity_violations=0,
        )

        snapshot = calculate_snapshots([source])[0]

        self.assertEqual(snapshot.performance.status, WatchlistStatus.NORMAL)
        self.assertEqual(snapshot.volume_context, "Low volume — rate-sensitive")


if __name__ == "__main__":
    unittest.main()
