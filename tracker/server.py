#!/usr/bin/env python3
"""Dashboard server: 127.0.0.1:8787, no login (removed at the user's request)."""
import base64, hmac, json, pathlib, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = pathlib.Path(__file__).resolve().parent
FILES = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"),
         "/data.json": ("data.json", "application/json")}

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/data.json":  # re-merge on every request so log appends show up
            subprocess.run([sys.executable, str(HERE / "sync.py")], capture_output=True)
        link = HERE / ".resume_link.json"  # temporary resume link written by ../resume_link.py (expires after 60 min)
        if link.exists() and time.time() - link.stat().st_mtime < 3600:
            spec = json.loads(link.read_text())
            if path == spec["path"]:
                body = pathlib.Path(spec["file"]).read_bytes()
                self.send_response(200); self.send_header("Content-Type", "application/pdf")
                self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body); return
        if path == "/go":  # tab jump: http://127.0.0.1:8787/go?tab=<chrome tab id>&u=<job url>; local only, never via the tunnel
            if not (self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")):
                self.send_error(403); return
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            sys.path.insert(0, str(HERE.parent)); import tabjump
            res = tabjump.jump(q.get("tab", [""])[0], q.get("u", [""])[0])
            body = f"<!doctype html><meta charset=utf-8><title>Tab jump</title><body style='font:14px system-ui;padding:24px'>Chrome tab {res}. You can close this tab.</body>".encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        if path not in FILES:
            self.send_error(404); return
        name, ctype = FILES[path]
        try:
            body = (HERE / name).read_bytes()
        except OSError:
            self.send_error(404); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8787), H).serve_forever()
