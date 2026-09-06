from __future__ import annotations

import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from sese_board_game.engine import run_command


ROOT = Path(__file__).resolve().parent
DIST_PATH = ROOT / "frontend" / "preview" / "dist"
SAVE_PATH = Path(tempfile.gettempdir()) / "sese-board-game-preview.json"


class PreviewHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        suffix = path.suffix.lower()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".ico": "image/x-icon",
        }.get(suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json({"ok": True})
            return
        if path == "/state":
            self._send_json(run_command("status", save_path=SAVE_PATH))
            return

        relative = path.lstrip("/")
        target = (DIST_PATH / relative).resolve() if relative else DIST_PATH / "index.html"
        try:
            target.relative_to(DIST_PATH.resolve())
        except ValueError:
            self.send_error(404)
            return
        if target.is_file():
            self._send_file(target)
        else:
            self._send_file(DIST_PATH / "index.html")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/command":
            self._send_json({"ok": False, "error": "not found"}, status=404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            command = str(body.get("command") or "").strip() or "status"
            self._send_json(run_command(command, save_path=SAVE_PATH))
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[preview] {self.address_string()} - {fmt % args}")


def main() -> None:
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), PreviewHandler)
    print(f"Sese Board Game web server listening on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
