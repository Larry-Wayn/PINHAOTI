import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinhaoti.selection import parse_selections


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((ROOT / "data" / "index.json").read_text())

    def test_chinese_and_compact_input_group_by_actual_year_type(self):
        selections = parse_selections("2009年数学一第9题\n2007-9\n2020年数学一第15题", self.index)
        self.assertEqual([(s.year, s.number, s.kind, s.output_number) for s in selections], [
            (2007, 9, "choice", 1),
            (2009, 9, "fill", 2),
            (2020, 15, "solution", 3),
        ])

    def test_duplicate_entries_are_included_once(self):
        selections = parse_selections("2009-9，2009年数学一第9题", self.index)
        self.assertEqual(len(selections), 1)

    def test_2021_last_question_is_available_but_23_is_not(self):
        selections = parse_selections("2021-10\n2021-16\n2021-22", self.index)
        self.assertEqual([(s.number, s.kind) for s in selections], [
            (10, "choice"), (16, "fill"), (22, "solution"),
        ])
        with self.assertRaises(ValueError):
            parse_selections("2021-23", self.index)

    def test_invalid_and_missing_question_reports_line(self):
        with self.assertRaisesRegex(ValueError, "第2项"):
            parse_selections("2009-9\n2022-9", self.index)
        with self.assertRaisesRegex(ValueError, "第1项"):
            parse_selections("2009年数学二第9题", self.index)


if __name__ == "__main__":
    unittest.main()
