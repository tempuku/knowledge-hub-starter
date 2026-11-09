#!/usr/bin/env python3
"""Generic smoke checks for initial and future OKF diary entries."""
import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", default="dist")
parser.add_argument("--public-only", action="store_true")
a = parser.parse_args()
output = (ROOT / a.output_dir).resolve()
source = ROOT / "openwiki/journal"
calendar = json.loads((output / "data/calendar.json").read_text(encoding="utf-8"))
assert calendar["format"] == "knowledge-hub-calendar-v1"
assert calendar["total"] == sum(x["count"] for x in calendar["days"])
assert (output / "index.html").exists() and (output / "app.js").exists()
assert (output / "sw.js").exists() and (output / "manifest.webmanifest").exists()
for icon in ("apple-touch-icon.png", "icon-192.png", "icon-512.png"):
    assert (output / icon).read_bytes()[:8] == b"\\x89PNG\\r\\n\\x1a\\n"

expected = set()
for p in source.rglob("*.md"):
    rel = p.relative_to(source).as_posix()
    if not re.fullmatch(r"\d{4}/\d{2}/\d{2}/[a-z0-9-]+\.md", rel):
        continue
    if p.name in {"index.md", "log.md"}:
        continue
    content = p.read_text(encoding="utf-8")
    metadata = yaml.safe_load(content.split("---", 2)[1])
    if a.public_only and metadata.get("visibility", "private") != "public":
        continue
    day = "-".join(p.relative_to(source).parts[:3])
    expected.add(day + "-" + p.stem)

seen = set()
for day in calendar["days"]:
    meta = json.loads((output / "data/days" / (day["date"] + ".json")).read_text())
    assert meta["count"] == day["count"]
    assert meta["pages"] >= 1 and meta["page_size"] == 50
    found = 0
    for page in range(1, meta["pages"] + 1):
        shard = output / "data/days" / day["date"] / (str(page) + ".json")
        rows = json.loads(shard.read_text())
        assert 1 <= len(rows) <= 50
        found += len(rows)
        for note in rows:
            assert note["id"] not in seen
            seen.add(note["id"])
            item = json.loads((output / "data/entries" / (note["id"] + ".json")).read_text())
            assert item["date"] == day["date"] and item["body"]
    assert found == day["count"]
assert seen == expected, ("missing", sorted(expected - seen), "extra", sorted(seen - expected))
print(f"Diary smoke check passed: {len(seen)} included entries, public_only={a.public_only}")
