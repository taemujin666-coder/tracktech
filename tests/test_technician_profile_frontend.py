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

    def test_profile_has_order_search_and_combined_donut(self):
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('id="jobHistorySearch"', app_source)
        self.assertIn("job.job_no", app_source)
        self.assertIn("combinedSignalCard(profile)", app_source)
        self.assertIn("conic-gradient", styles)

    def test_case_history_shows_recorded_resolution_date(self):
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("วันที่แก้ไข", app_source)
        self.assertIn("formatDate(item.close_date)", app_source)

    def test_profile_replaces_secondary_scores_with_case_insights(self):
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("countCard('QC Fail'", app_source)
        self.assertNotIn("countCard('Service Mind'", app_source)
        self.assertNotIn("countCard('QC มีหลักฐาน'", app_source)
        self.assertIn("rankedInsightCard('ISSUE CATEGORY'", app_source)
        self.assertIn("rankedInsightCard('ROOT CAUSE'", app_source)
        self.assertIn("actionLevelCard(insights.action_level)", app_source)

    def test_case_history_includes_project_and_dashboard_layout(self):
        app_source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("item.project_name", app_source)
        self.assertIn("<th>Project</th>", app_source)
        self.assertIn("case-history-table", styles)


if __name__ == "__main__":
    unittest.main()
