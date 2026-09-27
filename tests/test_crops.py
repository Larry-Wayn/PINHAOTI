import json
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinhaoti.crops import render_question, trim_ink


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


if __name__ == "__main__":
    unittest.main()
