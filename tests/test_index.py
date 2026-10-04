import sys
import json
import numpy as np
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_index import Marker, build_regions, choose_start, question_number, select_sequence


class IndexTests(unittest.TestCase):
    def test_question_number_accepts_fullwidth_and_ascii_parentheses(self):
        self.assertEqual(question_number("（9）设函数"), 9)
        self.assertEqual(question_number("(23) 求解"), 23)
        self.assertEqual(question_number("4）设 R 为幂级数"), 4)
        self.assertIsNone(question_number("（A）选项"))
        self.assertIsNone(question_number("求(2)的值"))

    def test_build_regions_keeps_cross_page_continuation(self):
        markers = [Marker(1, 0, 0.12, 0.05), Marker(2, 0, 0.62, 0.05), Marker(3, 1, 0.30, 0.05)]
        regions = build_regions(markers, page_count=2, headings={})
        self.assertEqual([(s["page"], s["top"], s["bottom"]) for s in regions.get(2, [])], [(0, 0.61, 0.96), (1, 0.04, 0.29)])

    def test_build_regions_stops_before_section_heading(self):
        markers = [Marker(8, 0, 0.40, 0.05), Marker(9, 0, 0.60, 0.05)]
        regions = build_regions(markers, page_count=1, headings={0: [0.55]})
        self.assertEqual(regions.get(8, [{}])[0].get("bottom"), 0.54)

    def test_build_regions_handles_question_at_top_of_next_page(self):
        markers = [Marker(1, 0, 0.80, 0.05), Marker(2, 1, 0.023, 0.05)]
        regions = build_regions(markers, page_count=2, headings={})
        self.assertEqual(len(regions[1]), 1)
        self.assertEqual(regions[2][0]["top"], 0.013)

    def test_select_sequence_ignores_ocr_false_positive(self):
        candidates = [Marker(1, 0, 0.10, 0.05), Marker(10, 0, 0.15, 0.05), Marker(2, 0, 0.20, 0.05), Marker(3, 0, 0.30, 0.05)]
        self.assertEqual([m.number for m in select_sequence(candidates, expected_count=3)], [1, 2, 3])

    def test_choose_start_accepts_a_short_white_gap(self):
        rows = np.full(1000, 100)
        rows[470:475] = 0
        self.assertLess(choose_start(rows, marker_y=0.50, lower_y=0.43, blank_threshold=10), 0.50)

    def test_bundled_index_covers_2007_through_2025_with_actual_question_counts(self):
        path = Path(__file__).resolve().parents[1] / "data" / "index.json"
        self.assertTrue(path.exists())
        years = json.loads(path.read_text())["years"]
        self.assertEqual(set(years), {str(y) for y in range(2007, 2026)})
        for year, paper in years.items():
            with self.subTest(year=year):
                count = 22 if int(year) >= 2021 else 23
                self.assertEqual(set(paper["questions"]), {str(n) for n in range(1, count + 1)})
                self.assertTrue(all(question["segments"] for question in paper["questions"].values()))
        self.assertEqual(years["2007"]["questions"]["11"]["type"], "fill")
        self.assertEqual(years["2007"]["questions"]["17"]["type"], "solution")
        self.assertEqual(years["2021"]["questions"]["10"]["type"], "choice")
        self.assertEqual(years["2021"]["questions"]["11"]["type"], "fill")
        self.assertEqual(years["2021"]["questions"]["16"]["type"], "fill")
        self.assertEqual(years["2021"]["questions"]["17"]["type"], "solution")
        self.assertEqual(years["2021"]["questions"]["22"]["type"], "solution")
        for year in range(2022, 2026):
            paper = years[str(year)]
            self.assertEqual(paper["fill_start"], 11)
            self.assertEqual(paper["solution_start"], 17)
            self.assertEqual(paper["questions"]["10"]["type"], "choice")
            self.assertEqual(paper["questions"]["11"]["type"], "fill")
            self.assertEqual(paper["questions"]["17"]["type"], "solution")
        self.assertLessEqual(years["2025"]["questions"]["22"]["segments"][-1]["page"], 6)

    def test_tall_formulas_start_with_their_own_question(self):
        years = json.loads((Path(__file__).resolve().parents[1] / "data" / "index.json").read_text())["years"]
        self.assertLess(years["2007"]["questions"]["11"]["segments"][0]["top"], 0.30)
        self.assertLess(years["2012"]["questions"]["5"]["segments"][0]["top"], 0.60)
        self.assertLess(years["2020"]["questions"]["13"]["segments"][0]["top"], 0.08)
        self.assertGreater(years["2020"]["questions"]["9"]["segments"][0]["top"], 0.700)
        self.assertLess(years["2020"]["questions"]["9"]["segments"][0]["top"], 0.707)
        self.assertLess(years["2012"]["questions"]["6"]["segments"][0]["top"], 0.72)
        self.assertLess(years["2012"]["questions"]["10"]["segments"][0]["top"], 0.15)
        self.assertLessEqual(years["2012"]["questions"]["4"]["segments"][0]["bottom"], years["2012"]["questions"]["5"]["segments"][0]["top"])

    def test_2015_illustration_overlap_has_explicit_margins(self):
        years = json.loads((Path(__file__).resolve().parents[1] / "data" / "index.json").read_text())["years"]
        first = years["2015"]["questions"]["1"]["segments"][0]
        second = years["2015"]["questions"]["2"]["segments"][0]
        self.assertGreater(first["top"], 0.15)
        self.assertGreater(first["bottom"], 0.30)
        self.assertTrue(first.get("masks"))
        self.assertTrue(second.get("masks"))
        self.assertLess(second["top"], 0.25)
        self.assertLessEqual(first["masks"][0]["y0"], second["top"])
        self.assertLessEqual(second["masks"][0]["x0"], 0.68)


if __name__ == "__main__":
    unittest.main()
