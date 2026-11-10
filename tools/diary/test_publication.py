#!/usr/bin/env python3
"""Deny accidental publication of private source, references, or unknown assets.

Run *after* --public-only build; the final Pages artifact must be exactly the
approved static application and authorized, individually paginated JSON files.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = (ROOT / (sys.argv[1] if len(sys.argv) > 1 else "dist-public")).resolve()
if not OUT.is_dir():
    raise SystemExit(f"No built public site at {OUT}")

STATIC = {
    "index.html", "app.js", "style.css", "sw.js", "manifest.webmanifest",
    "apple-touch-icon.png", "icon-192.png", "icon-512.png",
    "data/calendar.json",
}
SHARDED = (
    re.compile(r"data/days/\d{4}-\d{2}-\d{2}\.json"),
    re.compile(r"data/days/\d{4}-\d{2}-\d{2}/[1-9]\d*\.json"),
    re.compile(r"data/entries/\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.json"),
    re.compile(r"data/entries/log-[0-9a-f]{24}\.json"),
)
seen = set()
total_size = 0
for file in OUT.rglob("*"):
    if file.is_symlink():
        raise SystemExit(f"Symlinks forbidden in published preview: {file}")
    if not file.is_file():
        continue
    rel = file.relative_to(OUT).as_posix()
    if rel not in STATIC and not any(rule.fullmatch(rel) for rule in SHARDED):
        raise SystemExit(f"Unapproved published file: {rel}")
    if file.stat().st_size > 2_000_000:
        raise SystemExit(f"Unexpectedly large preview file: {rel}")
    if rel.startswith("data/"):
        json.loads(file.read_text(encoding="utf-8"))
    seen.add(rel)
    total_size += file.stat().st_size

if not STATIC.issubset(seen):
    raise SystemExit(f"Missing static files: {sorted(STATIC - seen)}")
if total_size > 100_000_000:
    raise SystemExit("Preview exceeds 100 MB publication budget")

html = (OUT / "index.html").read_text(encoding="utf-8")
if "BEGIN PRIVATE PROJECT LINKS" in html or "END PRIVATE PROJECT LINKS" in html:
    raise SystemExit("Unstripped private project section found in public HTML")
if "github.com/tempuku/" in html:
    raise SystemExit("Private source repository links found in public HTML")

calendar = json.loads((OUT / "data/calendar.json").read_text(encoding="utf-8"))
if calendar["total"] < 0:
    raise SystemExit("Invalid calendar metadata")
print(f"Publication allowlist passed: {len(seen)} static/JSON files, "
      f"{calendar['total']} explicitly public diary entries.")
