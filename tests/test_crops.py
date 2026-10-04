import json
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinhaoti.crops import _align_fragments, _erase_number, render_question, trim_ink


class CropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((ROOT / "data" / "index.json").read_text())

    def test_trimming_ignores_sparse_scan_speckle(self):
        image = Image.new("RGB", (400, 100), "white")
        draw = ImageDraw.Draw(image)
        draw.line((10, 20, 390, 20), fill="black", width=3)
        draw.point((50, 90), fill="black")
        cropped = trim_ink(image)
        self.assertLess(cropped.height, 50)
        self.assertGreater(cropped.height, 20)

    def test_cross_page_question_has_two_content_fragments(self):
        fragments = render_question(ROOT, self.index, 2009, 5, 1)
        self.assertEqual(len(fragments), 2)
        self.assertTrue(all(image.width > 600 and image.height > 30 for image in fragments))

    def test_blank_continuation_is_dropped(self):
        fragments = render_question(ROOT, self.index, 2020, 12, 1)
        self.assertEqual(len(fragments), 1)
        self.assertEqual(len(render_question(ROOT, self.index, 2008, 11, 1)), 1)
        self.assertEqual(len(render_question(ROOT, self.index, 2011, 10, 1)), 1)

    def test_numbers_share_a_column_across_years_and_digit_counts(self):
        right_edges = []
        for year, number, output_number in [(2007, 9, 1), (2012, 17, 9), (2021, 17, 10), (2024, 11, 99), (2025, 17, 100)]:
            with self.subTest(year=year, output_number=output_number):
                image = render_question(ROOT, self.index, year, number, output_number)[0]
                gutter = image.crop((0, 0, round(image.width * 0.065), image.height))
                box = ImageOps.invert(gutter.convert("L")).point(lambda p: 255 if p > 100 else 0).getbbox()
                self.assertIsNotNone(box)
                right_edges.append(box[2] / image.width)
        self.assertLess(max(right_edges) - min(right_edges), 0.003)

    def test_renumbering_does_not_change_question_content(self):
        first = render_question(ROOT, self.index, 2007, 9, 1)[0]
        second = render_question(ROOT, self.index, 2007, 9, 100)[0]
        self.assertEqual(first.size, second.size)
        content_box = (round(first.width * 0.065), 0, first.width, first.height)
        self.assertIsNone(ImageChops.difference(first.crop(content_box), second.crop(content_box)).getbbox())

    def test_wider_continuation_keeps_its_right_edge(self):
        first = Image.new("RGB", (400, 100), "white")
        ImageDraw.Draw(first).rectangle((80, 20, 200, 40), fill="black")
        continuation = Image.new("RGB", (800, 100), "white")
        ImageDraw.Draw(continuation).rectangle((700, 20, 780, 60), fill="blue")
        aligned = _align_fragments([first, continuation], 1, 25)
        self.assertTrue(any(color == (0, 0, 255) for count, color in aligned[1].getcolors(aligned[1].width * aligned[1].height)))

    def test_erasing_narrow_number_preserves_the_adjacent_lim(self):
        crop, marker_x, marker_y, width = self.number_crop(2020, 9)
        before = crop.copy()
        _erase_number(crop, marker_x, marker_y, width, int(width * 0.034))
        # In this scan the label is "9)" and lim starts immediately beside it.
        body = (marker_x + round(width * 0.022), 0, crop.width, crop.height)
        self.assertIsNone(ImageChops.difference(before.crop(body), crop.crop(body)).getbbox())

    def test_erasing_wide_number_removes_the_closing_parenthesis(self):
        crop, marker_x, marker_y, width = self.number_crop(2019, 1)
        _erase_number(crop, marker_x, marker_y, width, int(width * 0.034))
        label = crop.crop((marker_x, 0, marker_x + round(width * 0.039), marker_y + 16))
        self.assertIsNone(ImageOps.invert(label.convert("L")).point(lambda p: 255 if p > 65 else 0).getbbox())

    def number_crop(self, year, number):
        paper = self.index["years"][str(year)]
        segment = paper["questions"][str(number)]["segments"][0]
        document = pdfium.PdfDocument(str(ROOT / "sources" / paper["pdf"]))
        image = document[segment["page"]].render(scale=2.2).to_pil().convert("RGB")
        width, height = image.size
        x0, y0 = int(width * 0.02), int(height * segment["top"])
        crop = image.crop((x0, y0, int(width * 0.98), int(height * segment["bottom"])))
        return crop, int(width * segment["left"]) - x0, int(height * segment["marker_y"]) - y0, width


if __name__ == "__main__":
    unittest.main()
