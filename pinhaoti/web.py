from collections import OrderedDict
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
from urllib.parse import parse_qs, urlparse
import webbrowser

from .export import export_pdf
from .paths import resource_root
from .selection import parse_selections
from .ui import render_page


def verify_sources(root: Path, index: dict) -> int:
    count = 0
    for year, paper in index["years"].items():
        source = root / "sources" / paper["pdf"]
        if not source.is_file():
            raise FileNotFoundError(f"找不到 {year} 年试卷：{source}")
        if hashlib.sha256(source.read_bytes()).hexdigest() != paper["sha256"]:
            raise ValueError(f"{year} 年试卷与题目索引不匹配：{source}")
        count += 1
    return count


def make_server(root: Path, index: dict, port: int = 8787) -> ThreadingHTTPServer:
    previews: OrderedDict[str, bytes] = OrderedDict()
    quit_token = secrets.token_urlsafe(24)
    years = sorted(int(year) for year in index["years"])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def send_html(self, page: str, status: int = 200):
            data = page.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def send_pdf(self, pdf: bytes, attachment: bool):
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(pdf)))
            self.send_header("Content-Disposition", f'{"attachment" if attachment else "inline"}; filename="pinhaoti.pdf"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(pdf)

        def page(self, questions: str = "", space: str = "standard", error: str = "", preview: tuple[str, int] | None = None) -> str:
            return render_page(
                questions=questions, space=space, error=error, preview=preview,
                quit_token=quit_token, first_year=years[0], last_year=years[-1],
                paper_count=len(years),
            )

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self.send_html(self.page())
                return
            parts = path.strip("/").split("/")
            if len(parts) == 2 and parts[0] in ("pdf", "download") and parts[1] in previews:
                self.send_pdf(previews[parts[1]], attachment=parts[0] == "download")
                return
            self.send_error(404, "Not found")

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/quit":
                length = int(self.headers.get("Content-Length", "0"))
                if length > 1024:
                    self.send_error(413, "Request too large")
                    return
                fields = parse_qs(self.rfile.read(length).decode("utf-8"))
                supplied = fields.get("quit_token", [""])[0]
                if not secrets.compare_digest(supplied, quit_token):
                    self.send_error(403, "Forbidden")
                    return
                self.send_html("<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>拼好题已退出</title><p>拼好题已退出，可以关闭此页面。</p></html>")
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if path != "/preview":
                self.send_error(404, "Not found")
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > 65536:
                self.send_html(self.page(error="题号清单过长"), status=413)
                return
            fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            questions = fields.get("questions", [""])[0]
            space = fields.get("space", ["standard"])[0]
            try:
                selected = parse_selections(questions, index)
                document = export_pdf(root, index, selected, space)
            except (ValueError, FileNotFoundError) as exc:
                self.send_html(self.page(questions, space, str(exc)), status=400)
                return
            token = secrets.token_urlsafe(12)
            previews[token] = document
            while len(previews) > 5:
                previews.popitem(last=False)
            self.send_html(self.page(questions, space, preview=(token, len(selected))))

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    root = resource_root()
    index = json.loads((root / "data" / "index.json").read_text())
    count = verify_sources(root, index)
    server = make_server(root, index, port=0)
    address = f"http://127.0.0.1:{server.server_port}/"
    print(f"已核对 {count} 份真题。拼好题已启动：{address}", flush=True)
    if os.environ.get("PINHAOTI_NO_BROWSER") != "1":
        threading.Timer(0.5, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("已停止拼好题。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
