"""Check every generated equation and locally supplied browser dependency."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import json
import hashlib
from urllib.parse import urlsplit, parse_qs

SITE = Path(__file__).resolve().parents[3] / "docs/wiki/site"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.refs, self.remote = [], [], []
        self.formulas = self.svg = self.mathml = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "use":
            ref = a.get("xlink:href", a.get("href", ""))
            assert ref.startswith("#"), ref
            self.refs.append(ref[1:])
        if "arithmatex" in a.get("class", "").split():
            assert a.get("data-math-rendered") == "svg", "Unrendered equation"
            assert a.get("data-tex"), "Missing TeX source"
            self.formulas += 1
        if tag == "mjx-container":
            assert a.get("jax") == "SVG"
            self.svg += 1
        if tag == "mjx-assistive-mml":
            self.mathml += 1
        assert a.get("data-mml-node") != "merror", "MathJax rendering error"
        if tag in {"script", "link", "img", "iframe"}:
            url = a.get("src", a.get("href", ""))
            if url.startswith(("https://", "http://", "//")):
                self.remote.append(url)
            for resource in ("assets/stylesheets/mathjax-svg.css",
                             "assets/stylesheets/extra.css",
                             "assets/javascripts/theme-toggle.js",
                             "assets/javascripts/signal-labs.js"):
                if resource in url:
                    expected = hashlib.sha256((SITE / resource).read_bytes()).hexdigest()[:12]
                    assert parse_qs(urlsplit(url).query).get("v") == [expected], url
        if tag == "script":
            assert "mathjax" not in a.get("src", "").lower()


total = 0
pages = sorted(SITE.rglob("*.html"))
for path in pages:
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    assert page.formulas == page.svg == page.mathml, path
    assert not (set(page.refs) - set(page.ids)), path
    duplicates = [key for key, count in Counter(page.ids).items() if count > 1]
    assert not duplicates, (path, duplicates)
    assert not page.remote, (path, page.remote)
    total += page.formulas
assert total > 400
css = (SITE / "assets/stylesheets/mathjax-svg.css").read_text(encoding="utf-8")
assert "mjx-assistive-mml" in css and "clip:" in css
print(json.dumps({"pages": len(pages), "equations": total,
                  "remote_assets": 0, "broken_svg_references": 0}))
