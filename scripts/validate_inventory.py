#!/usr/bin/env python3
"""Validate a reviewed issue #35 inventory without changing source files.

This is deliberately separate from inventory_legacy.py: that generator's
--check mode compares only the pending inventory it creates. This validator
checks reviewed decisions against bytes and identities in the frozen Git tree.
It never generates migration output and never publishes records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import uuid
from collections import defaultdict
from urllib.parse import unquote

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/records"))
from validate_v1 import frontmatter as parse_frontmatter, safe_path as canonical_safe_path
ALLOWED_DISPOSITIONS = {"record", "duplicate-change", "summary-note", "structural"}
ALLOWED_TYPES = {"project", "note", "idea", "decision", "guide", "concept"}
ALLOWED_STATUSES = {"draft", "stable", "completed", "deprecated"}
ALLOWED_VISIBILITY = {"private", "public"}
REQUIRED_ITEM_FIELDS = {
    "old_path", "disposition", "destination_path", "allocated_record_id",
    "source_sha256", "legacy_log_path", "legacy_event_ids", "legacy_ui_ids",
    "project_mapping", "metadata_mapping", "occurrence_source", "review_notes",
}
UUID_FIELDS = (
    ("allocated_record_id", "record"),
)


class InventoryError(Exception):
    pass


def git(root: pathlib.Path, *args: str, text: bool = True):
    value = subprocess.check_output(["git", "-C", str(root), *args], text=text)
    return value.strip() if text else value


def frozen_paths(root: pathlib.Path, revision: str) -> list[str]:
    raw = git(root, "ls-tree", "-r", "--name-only", "-z", revision, "--", "openwiki", text=False)
    paths = [p.decode("utf-8") for p in raw.split(b"\0") if p]
    return sorted(p for p in paths if p.endswith(".md") and pathlib.PurePosixPath(p).name != "index.md")


def frozen_repo_paths(root: pathlib.Path, revision: str) -> set[str]:
    raw = git(root, "ls-tree", "-r", "--name-only", "-z", revision, text=False)
    return {p.decode("utf-8") for p in raw.split(b"\0") if p}


def frozen_bytes(root: pathlib.Path, revision: str, path: str) -> bytes:
    return git(root, "show", f"{revision}:{path}", text=False)


def is_uuid4(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
        return parsed.version == 4 and str(parsed) == value
    except (ValueError, AttributeError):
        return False


def fenced_events(raw: bytes, path: str) -> list[dict]:
    events = []
    for match in re.finditer(rb"```json\n(.*?)\n```", raw, re.S):
        try:
            obj = json.loads(match.group(1))
        except (ValueError, UnicodeError) as exc:
            raise InventoryError(f"{path}: malformed JSON legacy event: {exc}") from exc
        if not isinstance(obj, dict) or not isinstance(obj.get("id"), str):
            raise InventoryError(f"{path}: legacy event must be an object with string id")
        events.append(obj)
    return events


def scalar_frontmatter(raw: bytes) -> dict[str, str]:
    """Read legacy scalar fields used for explicit type/status/project checks."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if match and match.group(2) and not match.group(2).startswith("-"):
            val = match.group(2)
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            result[match.group(1)] = val
    return result


def full_frontmatter(raw: bytes, path: str) -> dict:
    try:
        text = raw.decode("utf-8")
        if not text.startswith("---\n"):
            return {}
        metadata, _ = parse_frontmatter(text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise InventoryError(f"{path}: cannot parse legacy YAML frontmatter: {exc}") from exc
    return metadata


def markdown_heading_slugs(text: str) -> set[str]:
    slugs, counts = set(), defaultdict(int)
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        heading = match.group(1).strip().lower()
        heading = re.sub(r"[`*_~]", "", heading)
        heading = re.sub(r"[^\w\-\s]", "", heading, flags=re.UNICODE)
        slug = re.sub(r"\s+", "-", heading).strip("-")
        counts[slug] += 1
        slugs.add(slug if counts[slug] == 1 else f"{slug}-{counts[slug]}")
    return slugs


def validate(data: dict, root: pathlib.Path = ROOT, manifest_label: str = "manifest") -> list[str]:
    errors: list[str] = []

    def fail(message: str):
        errors.append(message)

    if not isinstance(data, dict):
        return [f"{manifest_label}: top-level JSON must be an object"]
    required_root = {"schema_version", "base_revision", "review_status", "items",
                     "reviewed_source_revision", "record_count", "legacy_event_mappings",
                     "backfill_repair_plan", "normalization_event_allocations", "publication_eligibility",
                     "imported_baseline_allocations"}
    missing = sorted(required_root - data.keys())
    if missing:
        return [f"{manifest_label}: missing required root fields: {', '.join(missing)}"]
    if type(data.get("schema_version")) is not int or data.get("schema_version") != 1:
        fail("schema_version must be integer 1")
    revision = data.get("base_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        fail("base_revision must be a full lowercase Git commit SHA")
        return errors
    try:
        resolved = git(root, "rev-parse", "--verify", f"{revision}^{{commit}}")
    except subprocess.CalledProcessError:
        fail(f"base_revision does not resolve in Git repository: {revision}")
        return errors
    if resolved != revision:
        fail("base_revision must be the resolved full commit SHA")
    if data.get("review_status") != "reviewed-for-dry-run":
        fail("review_status must be reviewed-for-dry-run; pending manifests cannot pass")
    if data.get("reviewed_source_revision") != revision:
        fail("reviewed_source_revision must exactly equal base_revision")

    try:
        expected_paths = frozen_paths(root, revision)
    except subprocess.CalledProcessError as exc:
        fail(f"cannot enumerate frozen Git tree: {exc}")
        return errors
    items = data.get("items")
    if not isinstance(items, list):
        fail("items must be an array")
        return errors
    by_path = {}
    for index, item in enumerate(items):
        where = f"items[{index}]"
        if not isinstance(item, dict):
            fail(f"{where} must be an object")
            continue
        miss = REQUIRED_ITEM_FIELDS - item.keys()
        if miss:
            fail(f"{where} missing fields: {', '.join(sorted(miss))}")
            continue
        path = item.get("old_path")
        if not isinstance(path, str) or path in by_path:
            fail(f"{where}.old_path must be a unique path string")
            continue
        by_path[path] = item
        for list_field in ("legacy_event_ids", "legacy_ui_ids"):
            if not isinstance(item.get(list_field), list) or any(not isinstance(value, str) or not value.strip() for value in item.get(list_field, [])):
                fail(f"{path}: {list_field} must be an explicit array of non-empty strings")
        if path not in expected_paths:
            fail(f"{path}: not a non-index Markdown source in the frozen tree")
        elif isinstance(item.get("source_sha256"), str):
            try:
                actual_hash = hashlib.sha256(frozen_bytes(root, revision, path)).hexdigest()
                if not re.fullmatch(r"[0-9a-f]{64}", item["source_sha256"]) or item["source_sha256"] != actual_hash:
                    fail(f"{path}: source_sha256 does not match exact frozen source bytes")
            except (subprocess.CalledProcessError, ValueError) as exc:
                fail(f"{path}: cannot read frozen source bytes: {exc}")
        else:
            fail(f"{path}: source_sha256 must be an explicit lowercase SHA-256 digest")
        if item.get("disposition") not in ALLOWED_DISPOSITIONS:
            fail(f"{path}: unresolved or invalid disposition {item.get('disposition')!r}")
        notes = item.get("review_notes")
        if not isinstance(notes, str) or len(notes.strip()) < 8 or re.search(r"\b(UNREVIEWED|PENDING|TODO)\b", notes, re.I):
            fail(f"{path}: review_notes must contain a substantive reviewed rationale")
        # A wildcard is never an acceptable mapping or publication rule.
        def has_wildcard(value):
            if isinstance(value, dict):
                return any(k in ("*", "default", "wildcard") or has_wildcard(v) for k, v in value.items())
            if isinstance(value, list):
                return any(has_wildcard(v) for v in value)
            return isinstance(value, str) and value.strip() in {"*", "all", "default"}
        if any(has_wildcard(item.get(k)) for k in ("project_mapping", "metadata_mapping", "occurrence_source")):
            fail(f"{path}: wildcard/default mapping is forbidden")

    if set(by_path) != set(expected_paths):
        missing_paths = sorted(set(expected_paths) - set(by_path))
        extra_paths = sorted(set(by_path) - set(expected_paths))
        if missing_paths:
            fail(f"inventory omits frozen sources: {', '.join(missing_paths)}")
        if extra_paths:
            fail(f"inventory includes non-source paths: {', '.join(extra_paths)}")

    record_items = [i for i in items if isinstance(i, dict) and i.get("disposition") in ("record", "summary-note")]
    if data.get("record_count") != len(record_items):
        fail(f"record_count must equal retained record + summary-note count ({len(record_items)})")
    ids, destinations, target_casefold = {}, {}, {}
    project_ids = set()
    for item in record_items:
        path = item.get("old_path", "<unknown>")
        rid = item.get("allocated_record_id")
        dest = item.get("destination_path")
        meta = item.get("metadata_mapping")
        if not is_uuid4(rid):
            fail(f"{path}: retained record requires a stable UUIDv4 allocated_record_id")
        elif rid in ids:
            fail(f"{path}: allocated_record_id collides with {ids[rid]}")
        else:
            ids[rid] = path
        safe_destination = True
        if dest not in {"openwiki/CI.md", "openwiki/GUIDE.md"}:
            try:
                canonical_safe_path(dest, f"{path}.destination_path")
            except (ValueError, TypeError) as exc:
                safe_destination = False
                fail(f"{path}: retained record requires safe explicit destination_path ({exc})")
        if safe_destination:
            folded = dest.casefold()
            if folded in target_casefold:
                fail(f"{path}: destination case-fold collision with {target_casefold[folded]}")
            target_casefold[folded] = path
            destinations[dest] = path
        if not isinstance(meta, dict):
            fail(f"{path}: retained record requires explicit metadata_mapping object")
            continue
        for key in ("type", "title", "status", "visibility"):
            if key not in meta or meta[key] is None:
                fail(f"{path}: metadata_mapping.{key} must be explicit and non-null")
        if meta.get("type") not in ALLOWED_TYPES:
            fail(f"{path}: invalid/unknown reviewed type mapping {meta.get('type')!r}")
        if meta.get("status") not in ALLOWED_STATUSES:
            fail(f"{path}: invalid/unknown reviewed status mapping {meta.get('status')!r}")
        if meta.get("visibility") not in ALLOWED_VISIBILITY:
            fail(f"{path}: visibility must be private or public")
        title = meta.get("title")
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            fail(f"{path}: mapped title must be a non-empty string up to 200 characters")
        if "x_legacy" not in meta or not isinstance(meta["x_legacy"], dict):
            fail(f"{path}: metadata_mapping.x_legacy must explicitly preserve legacy extensions")
        try:
            legacy = full_frontmatter(frozen_bytes(root, revision, path), path)
        except (subprocess.CalledProcessError, InventoryError, ValueError) as exc:
            fail(f"{path}: cannot review legacy frontmatter: {exc}")
            legacy = {}
        src_type = legacy.get("type")
        expected_type = "note" if src_type in {"journal", "diary-entry"} else src_type
        if src_type and meta.get("type") != expected_type:
            fail(f"{path}: mapped type {meta.get('type')!r} does not preserve legacy type {src_type!r}")
        if src_type and meta.get("type") != src_type and meta.get("x_legacy", {}).get("type") != src_type:
            fail(f"{path}: transformed legacy type must be preserved in x_legacy.type")
        src_status = legacy.get("status")
        if src_status in ALLOWED_STATUSES and meta.get("status") != src_status:
            fail(f"{path}: mapped status changes known legacy status {src_status!r}")
        source_visibility = legacy.get("visibility")
        if source_visibility in ALLOWED_VISIBILITY and meta.get("visibility") != source_visibility:
            fail(f"{path}: mapped visibility changes explicit legacy visibility {source_visibility!r}")
        if source_visibility is None and meta.get("visibility") != "private":
            fail(f"{path}: missing legacy visibility defaults to private and cannot be widened")
        known_legacy_keys = {"type", "title", "status", "visibility", "description", "tags", "sources", "reminders", "occurred_on", "occurred_at", "project", "project_id", "id", "schema_version"}
        extensions = meta.get("x_legacy", {})
        for key, value in legacy.items():
            if key not in known_legacy_keys and extensions.get(key) != value:
                fail(f"{path}: unrecognized legacy metadata {key!r} must be preserved exactly under x_legacy")
        project = item.get("project_mapping")
        if meta.get("type") == "project":
            project_ids.add(rid)
            if not isinstance(project, dict) or project.get("record_id") != rid or project.get("legacy_slug") != legacy.get("project_id"):
                fail(f"{path}: project record mapping must map its legacy project_id to its own stable id")
            preserved_project_id = project.get("x_legacy_project_id", meta.get("x_legacy_project_id", meta.get("x_legacy", {}).get("project_id"))) if isinstance(project, dict) else None
            if preserved_project_id != legacy.get("project_id"):
                fail(f"{path}: project legacy project_id must be preserved under x_legacy_project_id")
        elif legacy.get("project"):
            if not isinstance(project, dict) or project.get("legacy_slug") != legacy.get("project"):
                fail(f"{path}: legacy project slug must have an explicit project_mapping")
        elif pathlib.PurePosixPath(path).name == "log.md" and isinstance(project, dict):
            if not isinstance(project.get("legacy_slug"), str) or not project.get("legacy_slug"):
                fail(f"{path}: summary project_mapping needs an explicit legacy_slug")
        elif project is not None:
            fail(f"{path}: source has no legacy project key, so project_mapping must be null")
        if isinstance(project, dict):
            target_id = project.get("record_id")
            if target_id is not None and not is_uuid4(target_id):
                fail(f"{path}: project_mapping.record_id must be UUIDv4 or explicit null with legacy preservation")
            if target_id is None and not isinstance(project.get("x_legacy_project"), str):
                fail(f"{path}: unresolved legacy project requires explicit x_legacy_project slug")
            if target_id is not None and target_id not in {x.get("allocated_record_id") for x in record_items if isinstance(x, dict)}:
                fail(f"{path}: project_mapping.record_id does not resolve to a retained record")
        occurrence = item.get("occurrence_source")
        if not (occurrence is None or (isinstance(occurrence, str) and occurrence.strip())):
            fail(f"{path}: occurrence_source must be an explicit source string or null")
        mapped_occurrence = meta.get("occurred_on") is not None or meta.get("occurred_at") is not None
        if mapped_occurrence:
            if not isinstance(occurrence, str) or not occurrence.strip():
                fail(f"{path}: mapped occurrence values require an explicit occurrence_source")
            elif not occurrence.startswith("legacy-frontmatter:"):
                fail(f"{path}: occurrence_source must identify its reviewed source field")
            else:
                legacy = full_frontmatter(frozen_bytes(root, revision, path), path)
                for field in ("occurred_on", "occurred_at"):
                    if field in meta and meta[field] != legacy.get(field):
                        fail(f"{path}: mapped {field} must preserve the exact legacy factual value")
        # Validate aliases declared on every item: no empty keys or duplicated key reuse.
        ui_keys = item.get("legacy_ui_ids")
        if not isinstance(ui_keys, list) or any(not isinstance(k, str) or not k.strip() for k in ui_keys):
            fail(f"{path}: legacy_ui_ids must be an explicit array of non-empty strings")

    for item in record_items:
        project = item.get("project_mapping")
        if isinstance(project, dict) and project.get("record_id") is not None and project.get("record_id") not in project_ids:
            fail(f"{item.get('old_path')}: project_mapping.record_id must reference a retained project record")

    # Canonical record destinations and their future sibling logs must be unique and safe.
    all_output_paths = {}
    for item in record_items:
        dest = item.get("destination_path")
        if not isinstance(dest, str):
            continue
        for output in (dest, dest[:-3] + ".log.md"):
            key = output.casefold()
            if key in all_output_paths and all_output_paths[key] != item.get("old_path"):
                fail(f"{item.get('old_path')}: target {output} collides with target of {all_output_paths[key]}")
            all_output_paths[key] = item.get("old_path")

    # Parse every existing log once; exact sequence and UI aliases are checked below.
    expected_event_map = {}
    event_by_key = {}
    declared_ui = {}
    source_logs = {}
    declared_logs = {}
    source_sequence_by_key = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        path = item.get("old_path")
        log_path = item.get("legacy_log_path")
        is_log_source = path and (path.endswith(".log.md") or pathlib.PurePosixPath(path).name == "log.md")
        if item.get("disposition") == "structural":
            if not is_log_source:
                fail(f"{path}: structural disposition must refer to a legacy log source")
            if item.get("destination_path") is not None or item.get("allocated_record_id") is not None:
                fail(f"{path}: structural item must not allocate a record or destination")
            archive = item.get("metadata_mapping")
            if not isinstance(archive, dict) or archive.get("archive_exact_bytes") is not True:
                fail(f"{path}: structural log requires explicit exact-byte archive disposition")
            elif archive.get("event_count") != len(item.get("legacy_event_ids", [])):
                fail(f"{path}: structural archive event_count must match its complete legacy event sequence")
        elif item.get("disposition") == "duplicate-change":
            # It may be a dated note whose UI id maps to an existing native event.
            if item.get("destination_path") is not None or item.get("allocated_record_id") is not None:
                fail(f"{path}: duplicate-change must not allocate a destination or record")
        elif item.get("disposition") == "summary-note":
            if not is_log_source or log_path is not None:
                fail(f"{path}: summary-note must be a unique directory log, not a record sibling log")
        elif item.get("disposition") == "record":
            if is_log_source:
                fail(f"{path}: native log source cannot be a record")
            if log_path is not None and log_path not in expected_paths:
                fail(f"{path}: legacy_log_path does not exist in frozen source tree")
            if log_path is None and not isinstance(item.get("legacy_event_ids"), list):
                fail(f"{path}: record without a native log requires explicit event mapping list")
        if isinstance(log_path, str):
            try:
                events = source_logs.get(log_path)
                if events is None:
                    raw = frozen_bytes(root, revision, log_path)
                    events = fenced_events(raw, log_path)
                    source_logs[log_path] = events
                declared = item.get("legacy_event_ids")
                if not isinstance(declared, list) or declared != [e["id"] for e in events]:
                    fail(f"{path}: legacy_event_ids must exactly preserve source event sequence from {log_path}")
                if log_path in declared_logs and declared_logs[log_path] != declared:
                    fail(f"{path}: conflicting event declarations for shared log {log_path}")
                declared_logs[log_path] = declared
                for source_sequence, event in enumerate(events, 1):
                    source_sequence_by_key[(log_path, event["id"])] = source_sequence
            except (subprocess.CalledProcessError, InventoryError) as exc:
                fail(f"{path}: cannot validate legacy log {log_path}: {exc}")
        elif item.get("legacy_event_ids"):
            fail(f"{path}: legacy_event_ids declared without a source legacy_log_path")
        for ui in item.get("legacy_ui_ids", []) if isinstance(item.get("legacy_ui_ids"), list) else []:
            if ui in declared_ui:
                fail(f"{path}: legacy UI key {ui!r} collides with {declared_ui[ui]}")
            declared_ui[ui] = path

    # Record items and their sibling log inventory items refer to the same
    # legacy event sequence. Build the canonical event index once per log.
    for log_path, events in source_logs.items():
        owner = next((i for i in record_items if i.get("legacy_log_path") == log_path), None)
        if owner is None:
            owner = next((i for i in items if isinstance(i, dict) and i.get("old_path") == log_path), None)
        for event in events:
            key = (log_path, event["id"])
            expected_event_map[key] = (owner, event)
            event_by_key[key] = event

    mappings = data.get("legacy_event_mappings")
    if not isinstance(mappings, list):
        fail("legacy_event_mappings must be an array")
        mappings = []
    mapped_keys, mapped_event_ids, mapped_record_sequences = set(), set(), defaultdict(list)
    legacy_operation_ids, legacy_idempotency_keys = set(), set()
    sequence_by_legacy_key = {}
    event_lookup = {}
    for n, mapping in enumerate(mappings):
        where = f"legacy_event_mappings[{n}]"
        if not isinstance(mapping, dict):
            fail(f"{where} must be an object")
            continue
        required = {"log_path", "legacy_event_id", "record_id", "sequence", "target_sequence", "allocated_event_id", "allocated_operation_id", "allocated_idempotency_key", "provenance_kind", "source_ref", "original_time", "source_action", "source_actor", "source_summary", "recorded_at_rule"}
        missing_fields = required - mapping.keys()
        if missing_fields:
            fail(f"{where} missing fields: {', '.join(sorted(missing_fields))}")
            continue
        key = (mapping["log_path"], mapping["legacy_event_id"])
        if mapping.get("sequence") != source_sequence_by_key.get(key):
            fail(f"{where}: sequence must preserve the exact legacy event order")
        if key in mapped_keys:
            fail(f"{where}: duplicate legacy event mapping for {key}")
        mapped_keys.add(key)
        pair = expected_event_map.get(key)
        if not pair:
            fail(f"{where}: mapping does not resolve to an actual event in the frozen source")
            continue
        item, event = pair
        expected_record = item.get("allocated_record_id")
        if item.get("disposition") == "structural":
            history_id = (item.get("metadata_mapping") or {}).get("history_for_record_id")
            if mapping.get("record_id") != history_id or not is_uuid4(history_id):
                fail(f"{where}: structural log event must map to explicit history_for_record_id")
        elif mapping.get("record_id") != expected_record or not is_uuid4(mapping.get("record_id")):
            fail(f"{where}: record_id does not match owning retained record")
        seq = mapping.get("target_sequence")
        sequence_by_legacy_key[key] = seq
        if type(seq) is not int or seq < 1:
            fail(f"{where}: sequence/target_sequence must be a positive integer")
        mapped_record_sequences[mapping.get("record_id")].append(seq)
        eid = mapping.get("allocated_event_id")
        if not is_uuid4(eid):
            fail(f"{where}: allocated_event_id must be UUIDv4")
        elif eid in mapped_event_ids:
            fail(f"{where}: allocated event UUID collides")
        else:
            mapped_event_ids.add(eid)
            event_lookup[eid] = (item, event, mapping)
        for field, pool in (("allocated_operation_id", legacy_operation_ids), ("allocated_idempotency_key", legacy_idempotency_keys)):
            value = mapping.get(field)
            if not is_uuid4(value) or value in pool:
                fail(f"{where}: {field} must be a unique lowercase UUIDv4")
            pool.add(value)
        for key_name, event_key in (("original_time", "timestamp"), ("source_action", "action"), ("source_actor", "actor"), ("source_summary", "summary")):
            if mapping.get(key_name) != event.get(event_key):
                fail(f"{where}: {key_name} must exactly preserve legacy {event_key}")
        if mapping.get("provenance_kind") not in {"legacy-log", "legacy-journal", "git-backfill"}:
            fail(f"{where}: invalid provenance_kind")
        if not isinstance(mapping.get("recorded_at_rule"), str) or not mapping["recorded_at_rule"].strip():
            fail(f"{where}: recorded_at_rule must be explicit")
        source_ref = mapping.get("source_ref")
        if source_ref != f"{mapping['log_path']}#{mapping['legacy_event_id']}":
            fail(f"{where}: source_ref must resolve to the exact legacy log event anchor")
    if mapped_keys != set(expected_event_map):
        for missing_key in sorted(set(expected_event_map) - mapped_keys):
            fail(f"missing legacy event mapping: {missing_key[0]}#{missing_key[1]}")
        for extra_key in sorted(mapped_keys - set(expected_event_map)):
            fail(f"unresolved extra legacy event mapping: {extra_key[0]}#{extra_key[1]}")
    if len(mappings) != len(expected_event_map):
        fail(f"legacy_event_mappings count {len(mappings)} does not equal source event count {len(expected_event_map)}")
    if set(ids) & mapped_event_ids:
        fail("allocated record UUIDs collide with allocated legacy event UUIDs")
    for rid, seqs in mapped_record_sequences.items():
        if len(seqs) != len(set(seqs)):
            fail(f"record {rid}: mapped target event sequences collide")

    # Every UI key is either the legacy log event key itself or has an explicit alias.
    ui_mappings = data.get("legacy_ui_mappings")
    if not isinstance(ui_mappings, list):
        fail("legacy_ui_mappings must explicitly resolve every declared legacy_ui_id")
        ui_mappings = []
    seen_ui, ui_to_event = set(), {}
    for n, alias in enumerate(ui_mappings):
        where = f"legacy_ui_mappings[{n}]"
        if not isinstance(alias, dict) or not {"legacy_ui_id", "record_id", "event_id", "resolution"}.issubset(alias):
            fail(f"{where} requires legacy_ui_id, record_id, event_id, and resolution")
            continue
        ui = alias.get("legacy_ui_id")
        if ui not in declared_ui:
            fail(f"{where}: UI key not declared by any inventory item")
        if ui in seen_ui:
            fail(f"{where}: UI key is mapped more than once")
        seen_ui.add(ui)
        if alias.get("record_id") not in ids:
            fail(f"{where}: record_id must resolve to a retained canonical record")
        if alias.get("source_path") != declared_ui.get(ui):
            fail(f"{where}: source_path must match the inventory item that declares this legacy UI key")
        event_id = alias.get("event_id")
        if event_id is not None and event_id not in event_lookup:
            fail(f"{where}: event_id does not resolve to a mapped legacy event")
        elif event_id is not None and event_lookup[event_id][2].get("record_id") != alias.get("record_id"):
            fail(f"{where}: event_id must resolve to the same canonical record as the UI alias")
        if not isinstance(alias.get("resolution"), str) or len(alias["resolution"].strip()) < 8:
            fail(f"{where}: resolution must give a concrete alias basis")
        ui_to_event[ui] = event_id
    if set(seen_ui) != set(declared_ui):
        for ui in sorted(set(declared_ui) - seen_ui):
            fail(f"missing legacy UI alias mapping: {ui} (from {declared_ui[ui]})")
        for ui in sorted(seen_ui - set(declared_ui)):
            fail(f"extra unresolved legacy UI alias: {ui}")

    repairs = data.get("backfill_repair_plan")
    if not isinstance(repairs, list):
        fail("backfill_repair_plan must be an array")
        repairs = []
    repair_events, repair_ops, repair_keys = set(), set(), set()
    repair_sequences = defaultdict(list)
    for n, plan in enumerate(repairs):
        where = f"backfill_repair_plan[{n}]"
        required = {"record_id", "source_path", "git_commit", "allocated_event_id", "provenance_kind", "original_time", "recorded_at_rule", "evidence", "before_bytes", "after_bytes", "before_sha256", "after_sha256", "allocated_operation_id", "allocated_idempotency_key", "insert_after_legacy_event_id", "insert_before_legacy_event_id", "target_sequence"}
        if not isinstance(plan, dict) or not required.issubset(plan):
            fail(f"{where} missing required repair evidence fields")
            continue
        event_id = plan.get("allocated_event_id")
        if not is_uuid4(event_id) or event_id in mapped_event_ids or event_id in repair_events:
            fail(f"{where}: repair event ID must be unique UUIDv4")
        repair_events.add(event_id)
        if plan.get("provenance_kind") != "git-backfill" or plan.get("original_time") is not None:
            fail(f"{where}: Git backfill must retain null original_time and git-backfill provenance")
        target_sequence = plan.get("target_sequence")
        if type(target_sequence) is not int or target_sequence < 1:
            fail(f"{where}: target_sequence must be an explicit positive integer")
        repair_sequences[plan.get("record_id")].append(target_sequence)
        if not isinstance(plan.get("evidence"), str) or len(plan["evidence"].strip()) < 16:
            fail(f"{where}: concrete evidence rationale is required")
        commit = plan.get("git_commit")
        try:
            commit = git(root, "rev-parse", "--verify", f"{commit}^{{commit}}")
            parent = git(root, "rev-parse", "--verify", f"{commit}^{{commit}}^1")
            before = frozen_bytes(root, parent, plan["source_path"])
            after = frozen_bytes(root, commit, plan["source_path"])
            if git(root, "merge-base", "--is-ancestor", commit, revision) is None: pass
        except subprocess.CalledProcessError as exc:
            fail(f"{where}: cited commit, parent, or source path does not resolve: {exc}")
            continue
        if len(before) != plan.get("before_bytes") or hashlib.sha256(before).hexdigest() != plan.get("before_sha256"):
            fail(f"{where}: before bytes/hash do not match cited Git parent")
        if len(after) != plan.get("after_bytes") or hashlib.sha256(after).hexdigest() != plan.get("after_sha256"):
            fail(f"{where}: after bytes/hash do not match cited Git commit")
        owning = next((i for i in record_items if i.get("allocated_record_id") == plan.get("record_id")), None)
        if owning is None or owning.get("old_path") != plan.get("source_path"):
            fail(f"{where}: repair source path must resolve to the retained record")
        else:
            log_path = owning.get("legacy_log_path")
            after_id = plan.get("insert_after_legacy_event_id")
            before_id = plan.get("insert_before_legacy_event_id")
            previous = expected_event_map.get((log_path, after_id)) if after_id else None
            following = expected_event_map.get((log_path, before_id)) if before_id else None
            if not previous:
                fail(f"{where}: insert_after_legacy_event_id must identify a source event for the retained record")
            elif previous[0] is not owning or type(previous[1].get("after")) is not str or previous[1]["after"].encode("utf-8") != before:
                fail(f"{where}: Git before snapshot must equal the exact after snapshot of the insertion anchor")
            if before_id:
                if not following:
                    fail(f"{where}: insert_before_legacy_event_id must identify a source event for the retained record")
                elif following[0] is not owning or type(following[1].get("before")) is not str or following[1]["before"].encode("utf-8") != after:
                    fail(f"{where}: Git after snapshot must equal the exact before snapshot of the following event")
                previous_sequence = sequence_by_legacy_key.get((log_path, after_id))
                if previous and type(target_sequence) is int and type(previous_sequence) is int and target_sequence != previous_sequence + 1:
                    fail(f"{where}: repair target_sequence must follow its source insertion anchor")
                following_sequence = sequence_by_legacy_key.get((log_path, before_id))
                if type(target_sequence) is int and type(following_sequence) is int and following_sequence != target_sequence + 1:
                    fail(f"{where}: following event target_sequence must follow the repair")
                if previous and following and source_sequence_by_key.get((log_path, before_id)) != source_sequence_by_key.get((log_path, after_id)) + 1:
                    fail(f"{where}: insertion anchors must be adjacent in the preserved legacy event order")
            elif after != frozen_bytes(root, revision, plan["source_path"]):
                fail(f"{where}: terminal Git backfill after snapshot must equal frozen current source bytes")
            elif source_sequence_by_key.get((log_path, after_id)) != len(source_logs.get(log_path, [])):
                fail(f"{where}: terminal Git backfill must follow the final legacy event")
        for field, pool in (("allocated_operation_id", repair_ops), ("allocated_idempotency_key", repair_keys)):
            value = plan.get(field)
            if not is_uuid4(value) or value in pool:
                fail(f"{where}: {field} must be unique UUIDv4")
            pool.add(value)
    # Verify backfill commit is in the ancestry of the frozen base.
    for plan in repairs:
        if isinstance(plan, dict) and isinstance(plan.get("git_commit"), str):
            proc = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", plan["git_commit"], revision], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc.returncode != 0:
                fail(f"backfill repair commit {plan['git_commit']} is not an ancestor of base_revision")
    for rid, seqs in repair_sequences.items():
        mapped_record_sequences[rid].extend(seqs)
    for rid, seqs in mapped_record_sequences.items():
        if sorted(seqs) != list(range(1, len(seqs) + 1)):
            fail(f"record {rid}: legacy plus repair target sequences must be exactly 1..N")

    baseline_allocations = data.get("imported_baseline_allocations")
    if not isinstance(baseline_allocations, list):
        fail("imported_baseline_allocations must be an array")
        baseline_allocations = []
    baseline_records, baseline_events, baseline_operations, baseline_keys = set(), set(), set(), set()
    expected_baseline_records = {i.get("allocated_record_id") for i in record_items if not i.get("legacy_log_path")}
    for n, allocation in enumerate(baseline_allocations):
        where = f"imported_baseline_allocations[{n}]"
        required = {"record_id", "source_path", "destination_path", "source_sha256", "action", "sequence", "before", "after_rule", "provenance_kind", "source_ref", "original_time", "recorded_at_rule", "allocated_event_id", "allocated_operation_id", "allocated_idempotency_key"}
        if not isinstance(allocation, dict) or not required.issubset(allocation):
            fail(f"{where} missing required baseline evidence fields")
            continue
        rid = allocation.get("record_id")
        owner = next((i for i in record_items if i.get("allocated_record_id") == rid), None)
        if owner is None or owner.get("old_path") != allocation.get("source_path") or owner.get("destination_path") != allocation.get("destination_path"):
            fail(f"{where}: baseline must resolve to one retained record and its reviewed source/destination")
        if rid in baseline_records:
            fail(f"{where}: duplicate imported baseline for record {rid}")
        baseline_records.add(rid)
        if allocation.get("action") != "IMPORTED" or allocation.get("sequence") != 1 or allocation.get("before") is not None:
            fail(f"{where}: no-history baseline must be IMPORTED sequence 1 with before null")
        if allocation.get("after_rule") != "exact frozen source bytes" or allocation.get("source_ref") != allocation.get("source_path"):
            fail(f"{where}: baseline must point to exact source bytes and preserve its source path")
        if allocation.get("provenance_kind") not in {"legacy-log", "legacy-journal"} or allocation.get("original_time") is not None:
            fail(f"{where}: baseline provenance must be explicit legacy provenance with null original_time")
        try:
            source = frozen_bytes(root, revision, allocation["source_path"])
            if allocation.get("source_sha256") != hashlib.sha256(source).hexdigest():
                fail(f"{where}: baseline source_sha256 does not match frozen content")
        except (subprocess.CalledProcessError, ValueError) as exc:
            fail(f"{where}: baseline source does not resolve: {exc}")
        if not isinstance(allocation.get("recorded_at_rule"), str) or not allocation["recorded_at_rule"].strip():
            fail(f"{where}: baseline recorded_at_rule must be explicit")
        for field, pool in (("allocated_event_id", baseline_events), ("allocated_operation_id", baseline_operations), ("allocated_idempotency_key", baseline_keys)):
            value = allocation.get(field)
            if not is_uuid4(value) or value in pool:
                fail(f"{where}: {field} must be a unique lowercase UUIDv4")
            pool.add(value)
        mapped_record_sequences[rid].append(1)
    if baseline_records != expected_baseline_records:
        fail("imported_baseline_allocations must contain exactly one baseline for every retained record without native history")
    if mapped_event_ids & baseline_events or set(ids) & baseline_events:
        fail("baseline event UUID collides with an existing legacy event or record UUID")

    allocations = data.get("normalization_event_allocations")
    if not isinstance(allocations, list):
        fail("normalization_event_allocations must be an array")
        allocations = []
    normalized_ids, operation_ids, idempotency_ids = set(), set(), set()
    by_record = {}
    for n, allocation in enumerate(allocations):
        where = f"normalization_event_allocations[{n}]"
        required = {"record_id", "source_path", "allocated_event_id", "allocated_operation_id", "allocated_idempotency_key", "recorded_at_rule"}
        if not isinstance(allocation, dict) or not required.issubset(allocation):
            fail(f"{where} missing required fields")
            continue
        rid = allocation.get("record_id")
        owner = next((i for i in record_items if i.get("allocated_record_id") == rid), None)
        if owner is None or owner.get("old_path") != allocation.get("source_path"):
            fail(f"{where}: allocation must match one retained record/source path")
        if rid in by_record:
            fail(f"{where}: duplicate normalization allocation for record {rid}")
        by_record[rid] = allocation
        for field, pool in (("allocated_event_id", normalized_ids), ("allocated_operation_id", operation_ids), ("allocated_idempotency_key", idempotency_ids)):
            value = allocation.get(field)
            if not is_uuid4(value) or value in pool:
                fail(f"{where}: {field} must be unique UUIDv4")
            pool.add(value)
        if not isinstance(allocation.get("recorded_at_rule"), str) or not allocation["recorded_at_rule"].strip():
            fail(f"{where}: recorded_at_rule must be explicit")
        target_sequence = allocation.get("target_sequence")
        prior_sequences = mapped_record_sequences.get(rid, [])
        if type(target_sequence) is not int or target_sequence != (max(prior_sequences) + 1 if prior_sequences else 1):
            fail(f"{where}: target_sequence must append exactly after preserved events/repairs/baseline")
        if target_sequence is not None:
            mapped_record_sequences[rid].append(target_sequence)
    if set(by_record) != {i.get("allocated_record_id") for i in record_items}:
        fail("normalization_event_allocations must contain exactly one allocation for every retained record")
    if mapped_event_ids & normalized_ids or repair_events & normalized_ids:
        fail("event UUIDs collide between legacy, repair, and normalization allocations")
    all_event_ids = mapped_event_ids | repair_events | baseline_events | normalized_ids
    if all_event_ids & set(ids):
        fail("allocated record UUIDs collide with allocated history event UUIDs")
    operation_sets = [legacy_operation_ids, repair_ops, baseline_operations, operation_ids]
    key_sets = [legacy_idempotency_keys, repair_keys, baseline_keys, idempotency_ids]
    for label, pools in (("operation IDs", operation_sets), ("idempotency keys", key_sets)):
        seen = set()
        for pool in pools:
            if seen & pool:
                fail(f"allocated {label} collide across legacy, repair, baseline, or normalization allocations")
            seen.update(pool)
    for rid, seqs in mapped_record_sequences.items():
        if sorted(seqs) != list(range(1, len(seqs) + 1)):
            fail(f"record {rid}: legacy, repair, baseline, and normalization sequences must be exactly 1..N")

    # Check direct source references in exact frozen source bytes and retained metadata.
    text_by_path = {}
    for path in expected_paths:
        try:
            text_by_path[path] = frozen_bytes(root, revision, path).decode("utf-8")
        except (subprocess.CalledProcessError, UnicodeDecodeError) as exc:
            fail(f"{path}: source must be readable UTF-8: {exc}")
    path_set = frozen_repo_paths(root, revision)
    for item in items:
        if not isinstance(item, dict) or item.get("disposition") not in ("record", "summary-note"):
            continue
        path = item.get("old_path")
        text = text_by_path.get(path, "")
        links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
        metadata = item.get("metadata_mapping") or {}
        sources = metadata.get("sources", [])
        if not isinstance(sources, list):
            fail(f"{path}: metadata_mapping.sources must be an array")
            sources = []
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("resource"), str):
                fail(f"{path}: each mapped source needs an explicit resource")
                continue
            links.append(source["resource"])
        for href in links:
            href = href.strip().split()[0] if href.strip() else ""
            if not href or re.match(r"^(?:https?:|mailto:|tel:|data:|record:|//)", href, re.I):
                if href.lower().startswith("record:"):
                    record_match = re.match(r"^record:([0-9a-f-]{36})", href, re.I)
                    if not record_match or record_match.group(1) not in ids:
                        fail(f"{path}: unresolved record link {href}")
                continue
            if href.startswith("#"):
                target, fragment = path, unquote(href[1:])
            else:
                target_part, _, fragment = href.partition("#")
                target_part = unquote(target_part)
                target = __import__("posixpath").normpath(str((pathlib.PurePosixPath(path).parent / target_part).as_posix())) if target_part else path
                fragment = unquote(fragment)
            if target.endswith("/"):
                target += "index.md"
            elif target in {"openwiki", "openwiki/"}:
                target = "openwiki/index.md"
            if target not in path_set:
                fail(f"{path}: broken frozen-source link target {href!r} resolves to {target}")
                continue
            if fragment:
                anchors = markdown_heading_slugs(text_by_path.get(target, ""))
                if fragment not in anchors:
                    fail(f"{path}: missing frozen-source anchor {fragment!r} in {target}")

    pub = data.get("publication_eligibility")
    if not isinstance(pub, dict):
        fail("publication_eligibility must be an explicit object")
    else:
        required = {"policy", "record_ids", "event_ids", "actor_labels", "review_basis"}
        if not required.issubset(pub):
            fail(f"publication_eligibility missing: {', '.join(sorted(required - pub.keys()))}")
        if pub.get("policy") != "reviewed-proposal-only-no-deployment-authorization":
            fail("publication proposal must explicitly carry no deployment authorization")
        if not isinstance(pub.get("review_basis"), str) or len(pub["review_basis"].strip()) < 20:
            fail("publication_eligibility.review_basis must state the evidence basis")
        for key in ("record_ids", "event_ids", "actor_labels"):
            if not isinstance(pub.get(key), list) or any(not isinstance(x, str) or not x.strip() or x.strip() in {"*", "all", "default"} for x in pub.get(key, [])):
                fail(f"publication_eligibility.{key} must be an explicit finite array with no wildcard")
            elif len(pub[key]) != len(set(pub[key])):
                fail(f"publication_eligibility.{key} must not contain duplicate entries")
        pub_records, pub_events = pub.get("record_ids", []), pub.get("event_ids", [])
        eligible_source_actors = set()
        if any(rid not in ids for rid in pub_records):
            fail("publication proposal references an unknown retained record ID")
        for eid in pub_events:
            if eid not in event_lookup:
                fail(f"publication proposal references unmapped legacy event UUID {eid}")
                continue
            _, source_event, mapping = event_lookup[eid]
            if isinstance(mapping.get("source_actor"), str):
                eligible_source_actors.add(mapping["source_actor"])
            if mapping.get("record_id") not in pub_records:
                fail(f"publication event {eid} is not associated with an explicitly proposed record")
            if source_event.get("visibility") != "public":
                fail(f"publication event {eid} has non-public legacy visibility")
            for snap in (source_event.get("before"), source_event.get("after")):
                if snap is not None:
                    try:
                        fm = full_frontmatter(snap.encode("utf-8"), f"publication event {eid} snapshot")
                    except InventoryError as exc:
                        fail(f"publication event {eid} has an invalid snapshot frontmatter: {exc}")
                        fm = {}
                    if fm.get("visibility") != "public":
                        fail(f"publication event {eid} includes a non-public or unmarked snapshot")
        for rid in pub_records:
            owner = next((i for i in record_items if i.get("allocated_record_id") == rid), None)
            if owner and (owner.get("metadata_mapping") or {}).get("visibility") != "public":
                fail(f"publication record {rid} is not currently mapped public")
        if not set(pub.get("actor_labels", [])) <= eligible_source_actors:
            fail("publication actor_labels may include only source actors from explicitly eligible public events")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default="migration/records-v1.json")
    ap.add_argument("--root", default=str(ROOT), help="Git repository containing the frozen base revision")
    ap.add_argument("--report-json", help="write a machine-readable validation report to this path")
    args = ap.parse_args()
    path = pathlib.Path(args.manifest)
    if not path.is_absolute():
        path = pathlib.Path(args.root) / path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"FAIL: cannot read manifest {path}: {exc}", file=sys.stderr)
        return 1
    errors = validate(data, pathlib.Path(args.root).resolve(), str(path))
    report = {
        "schema_version": 1,
        "validator": "reviewed-inventory-v1",
        "manifest": str(path),
        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "base_revision": data.get("base_revision") if isinstance(data, dict) else None,
        "reviewed_source_revision": data.get("reviewed_source_revision") if isinstance(data, dict) else None,
        "result": "fail" if errors else "pass",
        "source_count": len(data.get("items", [])) if isinstance(data, dict) and isinstance(data.get("items"), list) else None,
        "legacy_event_mapping_count": len(data.get("legacy_event_mappings", [])) if isinstance(data, dict) and isinstance(data.get("legacy_event_mappings"), list) else None,
        "legacy_ui_mapping_count": len(data.get("legacy_ui_mappings", [])) if isinstance(data, dict) and isinstance(data.get("legacy_ui_mappings"), list) else None,
        "retained_record_count": data.get("record_count") if isinstance(data, dict) else None,
        "source_hashes": {item.get("old_path"): item.get("source_sha256") for item in data.get("items", []) if isinstance(item, dict)} if isinstance(data, dict) and isinstance(data.get("items"), list) else {},
        "issues": errors,
    }
    if args.report_json:
        report_path = pathlib.Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if errors:
        print(f"FAIL: reviewed inventory validation found {len(errors)} issue(s):")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: reviewed inventory reconciles {len(data['items'])} frozen sources, "
          f"{len(data['legacy_event_mappings'])} legacy events, "
          f"{len(data['legacy_ui_mappings'])} UI aliases, and {data['record_count']} retained records; "
          "no migration or publication performed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
