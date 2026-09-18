import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from app.application.import_contract import validate_workbook


class ImportContractTest(unittest.TestCase):
    def test_valid_workbook_is_accepted(self):
        workbook = Workbook()
        job = workbook.active
        job.title = "Job Data"
        job.append(["Job No", "Tech ID", "Project"])
        job.append(["JOB001", "T001", "The Mall"])
        complaint = workbook.create_sheet("Complaint Log")
        complaint.append(["Job No", "Tech ID", "Rework"])
        complaint.append(["JOB001", "T001", "No"])
        technician = workbook.create_sheet("Technician Master")
        technician.append(["Tech ID", "Name", "Vendor"])
        technician.append(["T001", "Somchai", "KSP"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.xlsx"
            workbook.save(path)
            result = validate_workbook(path)
        self.assertTrue(all(item.is_valid for item in result))

    def test_missing_required_column_is_rejected(self):
        workbook = Workbook()
        workbook.active.title = "Job Data"
        workbook.active.append(["Tech ID"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.xlsx"
            workbook.save(path)
            result = validate_workbook(path)
        job_data = result[0]
        self.assertIn("job_no", job_data.missing_columns)
        self.assertFalse(job_data.is_valid)


if __name__ == "__main__":
    unittest.main()

