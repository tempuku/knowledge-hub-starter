#!/usr/bin/env python3
"""Compatibility checks for the original iPad Air / iOS 12 web app.

These are static checks and metadata checks, not a substitute for an actual
Safari 12 device acceptance test.
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
site = ROOT / "site"
app = (site / "app.js").read_text(encoding="utf-8")
worker = (site / "sw.js").read_text(encoding="utf-8")
html = (site / "index.html").read_text(encoding="utf-8")
manifest = json.loads((site / "manifest.webmanifest").read_text(encoding="utf-8"))

# Optional chaining / nullish coalescing were added after Safari 12. Some
# modern DOM conveniences are similarly unavailable on the target device.
for expression in ("?.", "??", "replaceChildren(", "replaceAll(", "structuredClone("):
    assert expression not in app, f"Safari 12-incompatible application syntax: {expression}"
for expression in ("?.", "??", "replaceChildren(", "replaceAll("):
    assert expression not in worker, f"Safari 12-incompatible service worker syntax: {expression}"

assert "navigator.serviceWorker.register('./sw.js')" in app
assert "'serviceWorker' in navigator" in app
assert "addEventListener('fetch'" in worker
assert "caches.open" in worker
assert manifest["display"] == "standalone"
assert manifest["start_url"] == "./"
assert manifest["scope"] == "./"
assert any(icon.get("sizes") == "180x180" for icon in manifest["icons"])
assert any(icon.get("sizes") == "192x192" for icon in manifest["icons"])

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            self.meta.append(a)
        if tag == "link":
            self.links.append(a)

tags = Tags()
tags.feed(html)
assert any(m.get("name") == "apple-mobile-web-app-capable" and m.get("content") == "yes" for m in tags.meta)
assert any(m.get("name") == "apple-mobile-web-app-title" and m.get("content") == "Knowledge Hub" for m in tags.meta)
assert any(l.get("rel") == "manifest" and l.get("href") == "./manifest.webmanifest" for l in tags.links)
assert any(l.get("rel") == "apple-touch-icon" for l in tags.links)

# Published v1 uses the same legacy shell vocabulary. These are static
# guardrails only: they cannot replace local Chromium/WebKit visual acceptance.
v1_html = (site / "v1.html").read_text(encoding="utf-8")
v1_js = (site / "v1.js").read_text(encoding="utf-8")
v1_css = (site / "v1.css").read_text(encoding="utf-8")
for expression in ("?.", "??", "replaceChildren(", "replaceAll("):
    assert expression not in v1_js, f"Safari 12-incompatible v1 syntax: {expression}"
assert 'id="global-search-form"' in v1_html
assert 'id="build-state"' in v1_html
assert 'href="./style.css"' in v1_html and 'href="./v1.css"' in v1_html
assert ".app-navbar .app-identity" in v1_css, "Linked identity loses white navbar styling"
assert re.search(r"#global-search-form\s*\{[^}]*display:flex", v1_css), "Unstyled navbar search form"
assert re.search(r"@media\(max-width:719px\)\s*\{\s*\.app-navbar\s*\{\s*display:grid", v1_css), "Mobile navbar loses compact grid"
assert ".status[data-status=in_progress]" in v1_css, "In progress status loses its amber treatment"
assert "flex:1 1 130px" not in v1_css, "Column toolbar stretches each control to 130px on phones"
assert re.search(r"\.toolbar\s*\{[^}]*display:grid", v1_css), "Mobile toolbar loses compact grid"
assert "pageDesc.index.change_count" in v1_js, "Diary day headers lose their change count"
assert "var opened=day===openDay" in v1_js, "Diary expands every day instead of the latest non-empty day"
assert "#app .route-wrap > h1:focus" in v1_css, "Programmatic heading focus draws an amber border"
assert 'intro?intro.nextSibling' in v1_js, "Mobile Sections interrupts heading and intro"

print("iOS 12 and v1 mobile-shell source checks passed; physical device and browser rendering not tested.")
