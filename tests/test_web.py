import json
import re
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinhaoti.web import make_server, verify_sources


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((ROOT / "data" / "index.json").read_text())

    def test_source_files_match_index(self):
        self.assertEqual(verify_sources(ROOT, self.index), 15)

    def test_preview_then_download_pdf(self):
        server = make_server(ROOT, self.index, port=0)
        self.assertIsNotNone(server)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(base + "/") as response:
                self.assertIn("年份", response.read().decode())
            body = urlencode({"questions": "2009年数学一第9题", "space": "standard"}).encode()
            with urlopen(Request(base + "/preview", data=body)) as response:
                page = response.read().decode()
            match = re.search(r'src="(/pdf/[A-Za-z0-9_-]+)"', page)
            self.assertIsNotNone(match)
            with urlopen(base + match.group(1)) as response:
                self.assertTrue(response.read().startswith(b"%PDF"))
        finally:
            server.shutdown()
            server.server_close()

    def test_quit_button_rejects_wrong_token_and_stops_server(self):
        server = make_server(ROOT, self.index, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(base + "/") as response:
                page = response.read().decode()
            match = re.search(r'name="quit_token" value="([A-Za-z0-9_-]+)"', page)
            self.assertIsNotNone(match)
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base + "/quit", data=urlencode({"quit_token": "wrong"}).encode()))
            self.assertEqual(error.exception.code, 403)
            with urlopen(Request(base + "/quit", data=urlencode({"quit_token": match.group(1)}).encode())) as response:
                self.assertIn("已退出", response.read().decode())
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
        finally:
            if thread.is_alive():
                server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
