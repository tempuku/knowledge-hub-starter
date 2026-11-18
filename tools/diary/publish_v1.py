#!/usr/bin/env python3
"""Publish the v1 HTTP viewer from approved public legacy entries and native records.

This is a transitional read-model bridge, not a source migration or a writer.
Legacy records remain unchanged; no private source bypasses the approved
public-only exporter. Native v1 items require explicit per-ID approval.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "projection"))
from compose import build_projection
from deterministic import ProjectionError, generation_id, json_bytes, write_staging
from git_source import derive_aliases, load_revision
from publication import (
    audit_public, forbidden_public_references, select_public, validate_policy,
)

EXPORTER_VERSION = "public-v1-bridge-0.1"
ENTRY_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-([a-z0-9-]+)$")


def stable_uuid(label: str) -> str:
    data = bytearray(hashlib.sha256(("knowledge-hub-public-bridge:" + label).encode()).digest()[:16])
    data[6] = (data[6] & 15) | 0x40
    data[8] = (data[8] & 63) | 0x80
    return str(uuid.UUID(bytes=bytes(data)))


def source_path(note: dict) -> str:
    entry_id = note["id"]
    match = ENTRY_PATTERN.fullmatch(entry_id)
    if match:
        year, month, day, name = match.groups()
        return f"openwiki/journal/{year}/{month}/{day}/{name}.md"
    if re.fullmatch(r"log-[0-9a-f]{24}", entry_id):
        path = note.get("change", {}).get("record") or note.get("project")
        if isinstance(path, str) and path.startswith("openwiki/") and path.endswith(".md"):
            return path
    raise ProjectionError("public legacy entry is missing a traceable source path")


def commit_recorded_time(root: Path, commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", commit, "--", path],
        cwd=root, text=True, capture_output=True, check=True)
    value = result.stdout.strip()
    if not value:
        raise ProjectionError("public legacy entry has no recorded source commit")
    parsed = dt.datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ProjectionError("source commit missing timezone")
    return parsed.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean_body(value: str) -> str:
    if value.startswith("---\n"):
        end = value.find("\n---\n", 4)
        if end >= 0:
            value = value[end + 5:]
    return value.strip()


def legacy_items(directory: Path, commit: str):
    calendar = json.loads((directory / "data" / "calendar.json").read_text())
    if calendar.get("format") != "knowledge-hub-calendar-v1":
        raise ProjectionError("unexpected public diary input format")
    records, histories, summaries = [], {}, {}
    seen = set()
    for day in calendar["days"]:
        day_str = day["date"]
        meta = json.loads((directory / "data" / "days" / (day_str + ".json")).read_text())
        for number in range(1, meta["pages"] + 1):
            entries = json.loads((directory / "data" / "days" / day_str / (str(number) + ".json")).read_text())
            for summary in entries:
                source_id = summary["id"]
                if source_id in seen:
                    raise ProjectionError("duplicate public legacy source entry")
                seen.add(source_id)
                note = json.loads((directory / "data" / "entries" / (source_id + ".json")).read_text())
                if note["id"] != source_id or note["date"] != day_str:
                    raise ProjectionError("legacy day/entry mismatch")
                origin = source_path(note)
                recorded_at = note.get("timestamp") or commit_recorded_time(ROOT, commit, origin)
                parsed = dt.datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
                if parsed.utcoffset() is None:
                    raise ProjectionError("legacy event without a verified timestamp")
                recorded_at = parsed.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                rid = stable_uuid("record:" + source_id)
                eid = stable_uuid("event:" + source_id)
                title = note["title"]
                body = clean_body(note.get("body", ""))
                content = "# " + title + "\n\n" + (body or note.get("description") or "Imported public diary entry") + "\n"
                status = note.get("status", "draft")
                if status not in {"draft", "stable", "in_progress", "completed", "deprecated"}:
                    status = "draft"
                tags = note.get("tags", [])
                if not isinstance(tags, list):
                    tags = []
                tags = [t for t in tags if isinstance(t, str)][:31]
                if "legacy-import" not in tags:
                    tags.append("legacy-import")
                record = {
                    "id": rid, "title": title, "description": note.get("description", ""),
                    "type": "note", "status": status, "project_id": None, "tags": tags,
                    "area": "journal", "updated_at": recorded_at, "version": 1,
                    "content_bytes": len(content.encode("utf-8")), "content": content,
                    "path": origin, "links": [], "reminders": [],
                }
                # The event is a derived import projection only; it is not a
                # fabricated source mutation or new authored Git record.
                event = {
                    "id": eid, "record_id": rid, "sequence": 1, "action": "IMPORTED",
                    "recorded_at": recorded_at, "occurred_on": day_str, "occurred_at": None,
                    "actor": {"id": "redacted", "kind": "migration", "label": "Legacy import"},
                    "summary": note.get("description") or "Imported approved public diary entry",
                    "path_before": None, "path_after": origin, "before": None, "after": content,
                    "provenance": {"kind": "legacy-journal", "source_ref": source_id, "original_time": recorded_at},
                }
                event_summary = {
                    "id": eid, "record_id": rid, "sequence": 1, "action": "IMPORTED",
                    "recorded_at": recorded_at, "occurred_on": day_str, "occurred_at": None,
                    "summary": event["summary"], "title": title, "status": status,
                    "project_id": None, "tags": tags, "actor_label": "Legacy import",
                    "provenance_kind": "legacy-journal", "type": "note", "area": "journal",
                }
                records.append(record)
                histories[rid] = [event]
                summaries[eid] = event_summary
    if len(seen) != calendar["total"]:
        raise ProjectionError("published legacy records do not match public diary count")
    return records, histories, summaries


def publish(directory: Path) -> dict:
    if not (directory / "data" / "calendar.json").exists():
        raise ProjectionError("build the approved public-only legacy diary first")
    commit, tree, native_records, native_histories, native_summaries = load_revision(ROOT, "HEAD")
    policy_raw = subprocess.check_output(
        ["git", "show", f"{commit}:config/publication.json"], cwd=ROOT)
    policy, policy_digest = validate_policy(policy_raw)
    native, histories, summaries = select_public(
        native_records, native_histories, native_summaries, policy)
    native_aliases = derive_aliases(native_records, native_histories)
    selected_aliases = derive_aliases(native, histories)
    forbidden = forbidden_public_references(
        native_records, native_histories, native, histories,
        source_aliases=native_aliases, selected_aliases=selected_aliases)
    legacy, old_histories, old_summaries = legacy_items(directory, commit)
    records = native + legacy
    if len({r["id"] for r in records}) != len(records):
        raise ProjectionError("bridge record ID collision")
    if set(summaries).intersection(old_summaries):
        raise ProjectionError("bridge event ID collision")
    histories.update(old_histories)
    summaries.update(old_summaries)
    aliases = derive_aliases(records, histories)
    files = build_projection(records, histories, summaries, aliases=aliases)
    generation = generation_id(tree, EXPORTER_VERSION, policy_digest)
    manifest = {
        "schema_version": 1, "generation": generation,
        "source_revision": commit, "exporter_version": EXPORTER_VERSION,
        "policy_digest": policy_digest,
        "published_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "public", "root": f"g/{generation}/",
    }
    audit_public({**files, "manifest.json": json_bytes(manifest)}, forbidden, policy_digest=policy_digest)
    data_dir = directory / "data"
    generation_dir = data_dir / "g" / generation
    if generation_dir.exists():
        raise ProjectionError("refusing to overwrite immutable public generation")
    write_staging(generation_dir, files)
    temp = data_dir / ".manifest-v1.tmp"
    temp.write_bytes(json_bytes(manifest))
    os.replace(temp, data_dir / "manifest.json")
    # Publish the new v1 app as the root and preserve the original usable
    # legacy diary as a deliberate fallback at /legacy.html.
    shutil.copy2(directory / "index.html", directory / "legacy.html")
    shutil.copy2(ROOT / "site" / "v1.html", directory / "index.html")
    for name in ("v1.js", "v1_data.js", "v1_markdown.js", "v1.css"):
        shutil.copy2(ROOT / "site" / name, directory / name)
    vendor = directory / "vendor"
    vendor.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "site" / "vendor" / "markdown-it-13.0.2.min.js",
                 vendor / "markdown-it-13.0.2.min.js")
    print(f"Published v1 HTTP demo: {len(records)} approved records "
          f"({len(native)} native, {len(legacy)} legacy diary entries)")
    return {"native": len(native), "legacy": len(legacy),
            "record_count": len(records), "event_count": len(summaries),
            "generation": generation}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="dist-public")
    args = parser.parse_args()
    print(json.dumps(publish((ROOT / args.output_dir).resolve()), indent=2))
