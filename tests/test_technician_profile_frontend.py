import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TechnicianProfileFrontendTest(unittest.TestCase):
    def test_watchlist_links_to_profile_route(self):
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('href="#technician/${encodeURIComponent(tech.technician_id)}"', app_source)
        self.assertIn("/api/technicians/${encodeURIComponent(technicianId)}", app_source)

    def test_profile_focuses_on_individual_job_case_and_review_sections(self):
        index_source = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('data-route-section="technician"', index_source)
        self.assertNotIn("TEAM SUMMARY", app_source)
        for label in ("JOB HISTORY", "CASE HISTORY", "HUMAN REVIEW"):
            self.assertIn(label, app_source)

    def test_profile_has_order_search_and_circular_scores(self):
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('id="jobHistorySearch"', app_source)
        self.assertIn("job.job_no", app_source)
        self.assertIn("combinedSignalCard(profile)", app_source)
        self.assertIn("profile.service_mind_cases", app_source)
        self.assertIn("conic-gradient", styles)

    def test_case_history_shows_recorded_resolution_date(self):
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("วันที่แก้ไข", app_source)
        self.assertIn("formatDate(item.close_date)", app_source)


if __name__ == "__main__":
    unittest.main()
