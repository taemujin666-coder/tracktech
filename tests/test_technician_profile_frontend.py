import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TechnicianProfileFrontendTest(unittest.TestCase):
    def test_watchlist_links_to_profile_route(self):
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('href="#technician/${encodeURIComponent(tech.technician_id)}"', app_source)
        self.assertIn("/api/technicians/${encodeURIComponent(technicianId)}", app_source)

    def test_profile_has_team_job_case_and_review_sections(self):
        index_source = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('data-route-section="technician"', index_source)
        for label in ("TEAM SUMMARY", "JOB HISTORY", "CASE HISTORY", "HUMAN REVIEW"):
            self.assertIn(label, app_source)


if __name__ == "__main__":
    unittest.main()
