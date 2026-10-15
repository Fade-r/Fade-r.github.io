from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[3]
SITE = ROOT / "docs" / "wiki" / "site"
FRAGMENT = ROOT / "workbench" / "experiments" / "wiki-build" / "iwr1443-parameter-lab.fragment.html"


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[tuple[str, str]] = []
        self.images = 0
        self.images_without_alt = 0
        self.iframes = 0
        self.iframes_without_title = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"a", "link"} and values.get("href"):
            self.urls.append(("href", values["href"] or ""))
        if tag in {"img", "script", "iframe", "source"} and values.get("src"):
            self.urls.append(("src", values["src"] or ""))
        if tag == "img":
            self.images += 1
            if not (values.get("alt") or "").strip():
                self.images_without_alt += 1
        if tag == "iframe":
            self.iframes += 1
            if not (values.get("title") or "").strip():
                self.iframes_without_title += 1


def local_target(page: Path, raw_url: str) -> Path | None:
    if raw_url.startswith(("http://", "https://", "mailto:", "data:", "javascript:", "#", "//")):
        return None
    parsed = urlsplit(raw_url)
    if not parsed.path:
        return None
    relative = Path(unquote(parsed.path.replace("/", str(Path("/")))))
    if parsed.path.startswith("/"):
        candidate = SITE / parsed.path.lstrip("/")
    else:
        candidate = page.parent / relative
    candidate = candidate.resolve()
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


def main() -> int:
    html_pages = sorted(SITE.rglob("*.html"))
    missing: list[dict[str, str]] = []
    windows_absolute: list[str] = []
    unresolved_snippets: list[str] = []
    total_images = 0
    total_iframes = 0
    alt_missing = 0
    iframe_titles_missing = 0

    for page in html_pages:
        text = page.read_text(encoding="utf-8")
        parser = AssetParser()
        parser.feed(text)
        total_images += parser.images
        total_iframes += parser.iframes
        alt_missing += parser.images_without_alt
        iframe_titles_missing += parser.iframes_without_title

        for kind, raw_url in parser.urls:
            target = local_target(page, raw_url)
            if target is not None and not target.exists():
                missing.append(
                    {
                        "page": str(page.relative_to(SITE)),
                        "attribute": kind,
                        "url": raw_url,
                        "resolved": str(target),
                    }
                )

        if re.search(r"[A-Za-z]:\\", text):
            windows_absolute.append(str(page.relative_to(SITE)))
        if "--8&lt;--" in text or "--8<--" in text:
            unresolved_snippets.append(str(page.relative_to(SITE)))

    forbidden_payloads = [
        str(path.relative_to(SITE))
        for path in SITE.rglob("*")
        if path.is_file() and path.suffix.lower() in {".bin", ".npz"}
    ]
    site_bytes = sum(path.stat().st_size for path in SITE.rglob("*") if path.is_file())
    fragment_text = FRAGMENT.read_text(encoding="utf-8")
    fragment_has_wrapper = bool(re.search(r"<!doctype|<html|<head|<body", fragment_text, re.I))

    report = {
        "html_pages": len(html_pages),
        "site_bytes": site_bytes,
        "local_missing": missing,
        "windows_absolute_pages": windows_absolute,
        "unresolved_snippets": unresolved_snippets,
        "forbidden_payloads": forbidden_payloads,
        "images": total_images,
        "images_without_alt": alt_missing,
        "iframes": total_iframes,
        "iframes_without_title": iframe_titles_missing,
        "fragment_bytes": FRAGMENT.stat().st_size,
        "fragment_has_wrapper": fragment_has_wrapper,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    failures = (
        missing
        or windows_absolute
        or unresolved_snippets
        or forbidden_payloads
        or alt_missing
        or iframe_titles_missing
        or fragment_has_wrapper
        or FRAGMENT.stat().st_size >= 2_000_000
        or len(html_pages) < 12
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
