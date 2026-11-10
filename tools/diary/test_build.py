#!/usr/bin/env python3
"""Generic smoke checks for initial and future OKF diary entries."""
import argparse
import hashlib
import json
import re
from datetime import datetime
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
    assert (output / icon).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

native_records = {p.relative_to(ROOT).as_posix()[:-7] + '.md' for p in (ROOT / 'openwiki').rglob('*.log.md')}
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
    change = metadata.get("change")
    if isinstance(change, dict) and change.get("record") in native_records:
        continue
    day = "-".join(p.relative_to(source).parts[:3])
    expected.add(day + "-" + p.stem)

# Independently enumerate native history entries.
FRONT = re.compile(r'\A---\r?\n(.*?)\r?\n---\r?\n', flags=re.S)
for log_file in (ROOT / "openwiki").rglob("*.log.md"):
    source_log = log_file.read_text(encoding="utf-8")
    blocks = re.findall(r"^## Entry ([a-z0-9-]+)\n```json\n(.*?)\n```(?:\n|$)", source_log, re.M | re.S)
    assert source_log.count("## Entry ") == len(blocks), log_file
    for entry_id, raw in blocks:
        entry = json.loads(raw)
        assert entry["id"] == entry_id
        if a.public_only:
            record_file = ROOT / entry["record"]
            record_meta = yaml.safe_load(FRONT.match(record_file.read_text()).group(1))
            if entry.get("visibility") != "public" or record_meta.get("visibility") != "public":
                continue
        expected.add("log-" + hashlib.sha256((entry["record"] + ":" + entry_id).encode()).hexdigest()[:24])

seen = set()
for day in calendar["days"]:
    meta = json.loads((output / "data/days" / (day["date"] + ".json")).read_text())
    assert meta["count"] == day["count"]
    assert meta["pages"] >= 1 and meta["page_size"] == 50
    found = 0
    timestamps = []
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
            timestamps.append(datetime.fromisoformat(note["timestamp"]).timestamp()
                              if "timestamp" in note else float("-inf"))
            if item.get("log_entry", {}).get("provenance") == "git-backfill":
                assert item["description"] == item["log_entry"]["action"].capitalize() + " record"
    assert found == day["count"]
    assert timestamps == sorted(timestamps, reverse=True), day["date"]
assert seen == expected, ("missing", sorted(expected - seen), "extra", sorted(seen - expected))
print(f"Diary smoke check passed: {len(seen)} included entries, public_only={a.public_only}")
