from io import BytesIO
import json
import sys
import unittest
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinhaoti.export import export_pdf
from pinhaoti.selection import parse_selections


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((ROOT / "data" / "index.json").read_text())

    def test_mixed_selection_has_a4_pages_and_source_map(self):
        selections = parse_selections("2007-9\n2009-9\n2020-15", self.index)
        pdf = export_pdf(ROOT, self.index, selections, "standard")
        self.assertTrue(pdf.startswith(b"%PDF"))
        reader = PdfReader(BytesIO(pdf))
        self.assertGreaterEqual(len(reader.pages), 2)
        self.assertTrue(all(round(float(page.mediabox.width)) == 595 for page in reader.pages))
        text = "\n".join(page.extract_text() for page in reader.pages)
        for label in ("选择题", "填空题", "解答题", "2007", "2009", "2020"):
            self.assertIn(label, text)

    def test_invalid_answer_space_is_rejected(self):
        with self.assertRaises(ValueError):
            export_pdf(ROOT, self.index, [], "huge")

    def test_pdf_uses_requested_title_without_page_headers_or_footers(self):
        selections = parse_selections("2007-9\n2009-9\n2020-15", self.index)
        reader = PdfReader(BytesIO(export_pdf(ROOT, self.index, selections, "standard")))
        text = "\n".join(page.extract_text() for page in reader.pages)

        self.assertIn("考研数学拼好题", text)
        self.assertNotIn("姓名：", text)
        self.assertNotIn("日期：", text)
        self.assertNotIn("考研数学一 · 真题精选卷", text)
        self.assertNotIn("数学一真题精选卷", text)
        self.assertNotIn("第 1 页", text)

    def test_section_heading_stays_with_first_solution(self):
        selections = parse_selections("2007-9\n2009-5\n2009-9\n2020-15", self.index)
        reader = PdfReader(BytesIO(export_pdf(ROOT, self.index, selections, "standard")))
        self.assertNotIn("解答题", reader.pages[0].extract_text())
        self.assertIn("解答题", reader.pages[1].extract_text())


if __name__ == "__main__":
    unittest.main()
