"""Local-only check: serve the built site with all scripts/fonts blocked."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parents[3] / "docs/wiki/site"


class NoScripts(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header(
            "Content-Security-Policy",
            "script-src 'none'; font-src 'none'; connect-src 'none'"
        )
        super().end_headers()


if __name__ == "__main__":
    ThreadingHTTPServer(
        ("127.0.0.1", 8766), partial(NoScripts, directory=str(SITE))
    ).serve_forever()
