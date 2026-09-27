import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinhaoti import web


class ResourcePathTests(unittest.TestCase):
    def test_frozen_app_uses_bundled_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys, "_MEIPASS", directory, create=True):
                self.assertTrue(hasattr(web, "resource_root"))
                self.assertEqual(web.resource_root(), Path(directory))

    def test_source_run_uses_project_root(self):
        self.assertTrue(hasattr(web, "resource_root"))
        self.assertEqual(web.resource_root(), ROOT)


if __name__ == "__main__":
    unittest.main()
