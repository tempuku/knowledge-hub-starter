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

print("iOS 12 source compatibility and install metadata checks passed; physical device not tested.")
