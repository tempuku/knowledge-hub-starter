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
sys.path.insert(0, str(ROOT / "tools" / "records"))
from compose import build_projection
from deterministic import ProjectionError, generation_id, json_bytes, write_staging
from git_source import derive_aliases, git, load_revision
from publication import (
    audit_public, forbidden_public_references, select_public, validate_policy,
)
from validate_v1 import frontmatter

# The public legacy bridge now emits one record per canonical source path and
# one event per approved diary entry, so the same source tree yields new bytes.
EXPORTER_VERSION = "public-v1-bridge-0.2"
ENTRY_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-([a-z0-9-]+)$")
LOG_ENTRY_PATTERN = re.compile(r"^log-[0-9a-f]{24}$")
LEGACY_LOG_ENTRY = re.compile(
    r"^## Entry ([a-z0-9-]+)\n```json\n(.*?)\n```(?:\n|$)", re.M | re.S)
STATUSES = {"draft", "stable", "in_progress", "completed", "deprecated"}
LEGACY_PROVENANCE = {"legacy-log", "legacy-journal", "git-backfill"}
PROJECT_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RECORD_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def stable_uuid(label: str) -> str:
    data = bytearray(hashlib.sha256(("knowledge-hub-public-bridge:" + label).encode()).digest()[:16])
    data[6] = (data[6] & 15) | 0x40
    data[8] = (data[8] & 63) | 0x80
    return str(uuid.UUID(bytes=bytes(data)))


def legacy_source_path(note: dict) -> str:
    """Resolve one approved diary entry to its canonical source file.

    Journal notes derive their path from the entry ID; update entries carry the
    record path in change.record. Anything missing or unsafe is rejected.
    """
    entry_id = note.get("id")
    match = ENTRY_PATTERN.fullmatch(entry_id or "")
    if match:
        year, month, day, name = match.groups()
        path = f"openwiki/journal/{year}/{month}/{day}/{name}.md"
    elif LOG_ENTRY_PATTERN.fullmatch(entry_id or ""):
        change = note.get("change")
        path = change.get("record") if isinstance(change, dict) else None
    else:
        raise ProjectionError("public legacy entry is missing a traceable source path")
    if not isinstance(path, str):
        raise ProjectionError("public legacy entry is missing a traceable source path")
    parts = path.split("/")
    if (not path.startswith("openwiki/") or not path.endswith(".md")
            or path.endswith(".log.md") or "\\" in path or "\0" in path
            or any(ord(char) < 32 or ord(char) == 127 for char in path)
            or len(path.encode("utf-8")) > 240
            or any(part in ("", ".", "..") for part in parts)
            or parts[-1] in ("index.md", "log.md")):
        raise ProjectionError("public legacy entry has an unsafe source path")
    return path


def utc_time(value: object, label: str) -> str:
    """Return an offset-qualified timestamp as UTC second-precision Z."""
    if not isinstance(value, str) or not value:
        raise ProjectionError(f"{label} has no verified timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectionError(f"{label} has an invalid timestamp") from exc
    if parsed.utcoffset() is None:
        raise ProjectionError(f"{label} timestamp is missing a timezone")
    return parsed.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def commit_recorded_time(root: Path, commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", commit, "--", path],
        cwd=root, text=True, capture_output=True, check=True)
    value = result.stdout.strip()
    if not value:
        raise ProjectionError("public legacy entry has no recorded source commit")
    return utc_time(value, "legacy source commit")


def first_added(root: Path, commit: str, path: str) -> tuple[str | None, str]:
    """Return the commit that added a source path and its UTC recorded time."""
    result = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H%x00%cI", "-1", commit, "--", path],
        cwd=root, text=True, capture_output=True, check=True)
    line = result.stdout.strip()
    if not line:
        return None, commit_recorded_time(root, commit, path)
    commit, separator, when = line.partition("\0")
    if not separator or not commit or not when:
        raise ProjectionError("cannot resolve the public legacy creation commit")
    return commit, utc_time(when, "legacy creation commit")


def read_blob(root: Path, commit: str, path: str, label: str) -> tuple[bytes, str]:
    raw = git(root, "show", f"{commit}:{path}")
    try:
        return raw, raw.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise ProjectionError(f"{label} is not valid UTF-8: {path}") from exc


def snapshot_digest(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProjectionError("legacy snapshot is not a string")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def legacy_log_entries(root: Path, commit: str, path: str) -> dict[str, dict]:
    """Parse only the immutable HEAD sibling log for one canonical path."""
    log_path = path[:-3] + ".log.md"
    _, text = read_blob(root, commit, log_path, "legacy public log")
    matches = list(LEGACY_LOG_ENTRY.finditer(text))
    if text.count("## Entry ") != len(matches):
        raise ProjectionError("malformed legacy public log: " + log_path)
    entries: dict[str, dict] = {}
    for match in matches:
        try:
            entry = json.loads(match.group(2))
        except ValueError as exc:
            raise ProjectionError("invalid legacy public log entry: " + log_path) from exc
        if not isinstance(entry, dict) or entry.get("id") != match.group(1):
            raise ProjectionError("legacy public log entry heading mismatch")
        if entry["id"] in entries:
            raise ProjectionError("duplicate legacy public log entry")
        entries[entry["id"]] = entry
    return entries


def note_event(root: Path, commit: str, path: str, entry_id: str, note: dict,
               day: str, head_meta: dict) -> dict:
    creation, recorded_at = first_added(root, commit, path)
    _, after = read_blob(root, creation or commit, path, "legacy creation snapshot")
    occurred_at = None
    value = head_meta.get("occurred_at")
    if isinstance(value, str) and value:
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if (parsed is not None and parsed.utcoffset() is not None
                and parsed.date().isoformat() == day):
            occurred_at = parsed.astimezone(dt.timezone.utc).isoformat(
                timespec="seconds").replace("+00:00", "Z")
    summary = note.get("description") or "Imported approved public diary entry"
    return {
        "id": stable_uuid("event:" + entry_id), "record_id": None, "sequence": 0,
        "action": "IMPORTED", "recorded_at": recorded_at,
        "occurred_on": day, "occurred_at": occurred_at,
        "actor": {"id": "redacted", "kind": "migration", "label": "Legacy import"},
        "summary": summary, "path_before": None, "path_after": path,
        "before": None, "after": after,
        "provenance": {"kind": "legacy-journal", "source_ref": entry_id,
                       "original_time": recorded_at},
    }


def log_event(entry_id: str, note: dict, path: str, entry: dict) -> dict:
    before, after = entry.get("before"), entry.get("after")
    if not isinstance(after, str) or (before is not None and not isinstance(before, str)):
        raise ProjectionError("legacy public log entry has invalid snapshots")
    if entry.get("record") != path:
        raise ProjectionError("legacy public log entry record mismatch")
    if entry.get("visibility") != "public":
        raise ProjectionError("non-public legacy log entry in the public projection")
    if snapshot_digest(before) != entry.get("before_sha256"):
        raise ProjectionError("legacy public log before snapshot hash mismatch")
    if snapshot_digest(after) != entry.get("after_sha256"):
        raise ProjectionError("legacy public log after snapshot hash mismatch")
    recorded_at = utc_time(entry.get("timestamp"), "legacy public log entry")
    approved = note.get("log_entry") if isinstance(note.get("log_entry"), dict) else {}
    if approved.get("after_sha256") not in (None, entry["after_sha256"]):
        raise ProjectionError("approved diary entry no longer matches its source log")
    if approved.get("timestamp") and utc_time(
            approved["timestamp"], "approved diary entry") != recorded_at:
        raise ProjectionError("approved diary entry timestamp drifted from its source log")
    action = entry.get("action")
    if not isinstance(action, str) or not action:
        action = "UPDATED"
    summary = entry.get("summary")
    if not isinstance(summary, str) or not summary:
        summary = f"{action.capitalize()} record"
    provenance = entry.get("provenance")
    if isinstance(provenance, dict):
        raise ProjectionError("native provenance in a legacy public log entry")
    # Legacy logs use free-form provenance labels; keep the reviewed category
    # when it is a projection kind and otherwise classify it as legacy history.
    kind = (provenance if isinstance(provenance, str)
            and provenance in LEGACY_PROVENANCE else "legacy-log")
    return {
        "id": stable_uuid("event:" + entry_id), "record_id": None, "sequence": 0,
        "action": action, "recorded_at": recorded_at,
        "occurred_on": None, "occurred_at": None,
        "actor": {"id": "redacted", "kind": "migration", "label": "Legacy import"},
        "summary": summary,
        "path_before": path if before is not None else None, "path_after": path,
        "before": before, "after": after,
        "provenance": {"kind": kind, "source_ref": entry_id,
                       "original_time": recorded_at},
    }


def _area(path: str) -> str:
    inner = path[len("openwiki/"):]
    return inner.rsplit("/", 1)[0] if "/" in inner else "root"


def _snapshot_metadata(snapshot: str) -> dict:
    try:
        metadata, _ = frontmatter(snapshot)
    except (ValueError, TypeError):
        # M-02 legacy snapshots may omit YAML; bytes stay exact and only the
        # historical display metadata falls back to Unknown.
        return {}
    return metadata if isinstance(metadata, dict) else {}


def _project_id(metadata: dict, project_links: dict[str, str]) -> str | None:
    slug = metadata.get("project")
    return project_links.get(slug) if isinstance(slug, str) else None


def event_summary(event: dict, project_links: dict[str, str]) -> dict:
    metadata = _snapshot_metadata(event["after"])
    record_type = metadata.get("type")
    record_type = ("note" if record_type == "diary-entry" else record_type
                   if isinstance(record_type, str) and record_type else "Unknown")
    status = metadata.get("status")
    if not isinstance(status, str) or not status:
        status = "Unknown"
    tags = metadata.get("tags")
    tags = [tag for tag in tags if isinstance(tag, str)] if isinstance(tags, list) else []
    title = metadata.get("title")
    if not isinstance(title, str) or not title:
        title = "Unknown"
    return {
        "id": event["id"], "record_id": event["record_id"], "operation_id": None,
        "sequence": event["sequence"], "action": event["action"],
        "recorded_at": event["recorded_at"], "occurred_on": event["occurred_on"],
        "occurred_at": event["occurred_at"], "summary": event["summary"],
        "title": title, "status": status,
        "project_id": _project_id(metadata, project_links),
        "tags": tags, "actor_label": "Legacy import",
        "provenance_kind": event["provenance"]["kind"], "type": record_type,
        "area": _area(event["path_after"]),
    }


def legacy_projection(directory: Path, commit: str, project_links: dict[str, str]):
    """Group approved public legacy entries into one record per source path."""
    calendar = json.loads((directory / "data" / "calendar.json").read_text())
    if calendar.get("format") != "knowledge-hub-calendar-v1":
        raise ProjectionError("unexpected public diary input format")
    groups: dict[str, dict] = {}
    seen = set()
    for day in calendar["days"]:
        day_str = day["date"]
        meta = json.loads((directory / "data" / "days" / (day_str + ".json")).read_text())
        for number in range(1, meta["pages"] + 1):
            entries = json.loads(
                (directory / "data" / "days" / day_str / (str(number) + ".json")).read_text())
            for summary in entries:
                source_id = summary["id"]
                if source_id in seen:
                    raise ProjectionError("duplicate public legacy source entry")
                seen.add(source_id)
                note = json.loads(
                    (directory / "data" / "entries" / (source_id + ".json")).read_text())
                if note["id"] != source_id or note["date"] != day_str:
                    raise ProjectionError("legacy day/entry mismatch")
                path = legacy_source_path(note)
                group = groups.setdefault(path, {"note": None, "logs": []})
                if ENTRY_PATTERN.fullmatch(source_id):
                    if group["note"] is not None:
                        raise ProjectionError("duplicate legacy journal note for one path")
                    group["note"] = (source_id, note, day_str)
                else:
                    group["logs"].append((source_id, note, day_str))
    if len(seen) != calendar["total"]:
        raise ProjectionError("published legacy records do not match public diary count")

    records, histories, summaries = [], {}, {}
    entry_aliases, current_aliases = {}, {}
    for path in sorted(groups):
        group = groups[path]
        if not group["note"] and not group["logs"]:
            continue
        raw, content = read_blob(ROOT, commit, path, "legacy public record")
        try:
            metadata, body = frontmatter(content)
        except (ValueError, TypeError) as exc:
            raise ProjectionError(
                "legacy public record has no traceable frontmatter: " + path) from exc
        if metadata.get("visibility") != "public":
            raise ProjectionError("non-public legacy record in the public projection")
        if group["note"]:
            base_id = group["note"][0]
        else:
            base_id = min(group["logs"], key=lambda item: (
                utc_time(item[1].get("timestamp"), "legacy public log entry"), item[0]))[0]
        record_id = stable_uuid("record:" + base_id)
        if record_id in histories:
            raise ProjectionError("legacy bridge record ID collision")

        events = []
        if group["note"]:
            entry_id, note, day = group["note"]
            events.append(note_event(ROOT, commit, path, entry_id, note, day, metadata))
        if group["logs"]:
            source = legacy_log_entries(ROOT, commit, path)
            for entry_id, note, _day in group["logs"]:
                approved = note.get("log_entry")
                legacy_id = approved.get("id") if isinstance(approved, dict) else None
                if not isinstance(legacy_id, str) or legacy_id not in source:
                    raise ProjectionError(
                        "approved diary entry has no matching legacy log entry")
                events.append(log_event(entry_id, note, path, source[legacy_id]))
        events.sort(key=lambda event: (event["recorded_at"], event["id"]))
        for sequence, event in enumerate(events, 1):
            event["record_id"] = record_id
            event["sequence"] = sequence

        title = metadata.get("title")
        if not isinstance(title, str) or not title:
            title = Path(path).stem
        description = metadata.get("description", "")
        if not isinstance(description, str):
            description = ""
        record_type = metadata.get("type")
        record_type = ("note" if record_type == "diary-entry" else record_type
                       if isinstance(record_type, str) and record_type else "note")
        status = metadata.get("status", "draft")
        if not isinstance(status, str) or status not in STATUSES:
            status = "draft"
        tags = metadata.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        tags = [tag for tag in tags if isinstance(tag, str)][:31]
        if "legacy-import" not in tags:
            tags.append("legacy-import")
        records.append({
            "id": record_id, "title": title, "description": description,
            "type": record_type, "status": status,
            "project_id": _project_id(metadata, project_links),
            "tags": tags, "area": _area(path),
            "updated_at": events[-1]["recorded_at"], "version": len(events),
            "content_bytes": len(raw), "content": content, "body": body,
            "path": path, "links": [], "reminders": [],
        })
        histories[record_id] = events
        for event in events:
            summaries[event["id"]] = event_summary(event, project_links)
            entry_id = event["provenance"]["source_ref"]
            entry_aliases[entry_id] = event["id"]
            old_record_id = stable_uuid("record:" + entry_id)
            if old_record_id != record_id:
                current_aliases[old_record_id] = record_id
    return records, histories, summaries, entry_aliases, current_aliases


def load_project_links(root: Path, commit: str) -> dict[str, str]:
    """Load the reviewed legacy project map from the immutable revision."""
    raw = git(root, "show", f"{commit}:config/project-links.json")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ProjectionError("invalid project link config JSON") from exc
    if type(data) is not dict or set(data) != {"schema_version", "legacy_projects"}:
        raise ProjectionError("unknown project link config schema")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ProjectionError("unknown project link config schema version")
    links = data["legacy_projects"]
    if type(links) is not dict:
        raise ProjectionError("invalid project link map")
    clean = {}
    for slug, target in links.items():
        if (not isinstance(slug, str) or not PROJECT_SLUG.fullmatch(slug)
                or not isinstance(target, str) or not RECORD_UUID.fullmatch(target)):
            raise ProjectionError("invalid project link mapping")
        clean[slug] = target
    return dict(sorted(clean.items()))


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
    project_links = load_project_links(ROOT, commit)
    legacy, old_histories, old_summaries, legacy_entries, legacy_current = \
        legacy_projection(directory, commit, project_links)
    records = native + legacy
    if len({r["id"] for r in records}) != len(records):
        raise ProjectionError("bridge record ID collision")
    if set(summaries).intersection(old_summaries):
        raise ProjectionError("bridge event ID collision")
    public_projects = {record["id"] for record in records if record["type"] == "project"}
    unresolved = set(project_links.values()) - public_projects
    if unresolved:
        raise ProjectionError("legacy project link target is not a public project record")
    histories.update(old_histories)
    summaries.update(old_summaries)
    # Native aliases stay authoritative; the legacy grouping only adds the
    # approved entry and old synthetic record identities it deliberately moved.
    aliases = derive_aliases(records, histories)
    for entry_id, event_id in legacy_entries.items():
        previous = aliases["entries"].get(entry_id)
        if previous is not None and previous != event_id:
            raise ProjectionError("contradictory legacy entry alias")
        aliases["entries"][entry_id] = event_id
    aliases["entries"] = dict(sorted(aliases["entries"].items()))
    if legacy_current:
        current = aliases.setdefault("current_entries", {})
        for old_record_id, record_id in legacy_current.items():
            previous = current.get(old_record_id)
            if previous is not None and previous != record_id:
                raise ProjectionError("contradictory legacy record alias")
            current[old_record_id] = record_id
        aliases["current_entries"] = dict(sorted(current.items()))
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
          f"({len(native)} native, {len(legacy)} legacy records, "
          f"{len(old_summaries)} legacy events)")
    return {"native": len(native), "legacy": len(legacy),
            "legacy_events": len(old_summaries),
            "record_count": len(records), "event_count": len(summaries),
            "generation": generation}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="dist-public")
    args = parser.parse_args()
    print(json.dumps(publish((ROOT / args.output_dir).resolve()), indent=2))
