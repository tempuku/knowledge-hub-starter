#!/usr/bin/env python3
"""Fail-closed review gate for M-01/M-03; does not authorize cutover.

Usage: python3 scripts/validate_inventory_review.py migration/records-v1.json
"""
import argparse
import json
import pathlib
import re
import sys
import uuid

DISPOSITIONS = {"record", "duplicate-change", "summary-note", "structural"}
UUID_FIELDS = ("allocated_record_id",)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = {
    "old_path", "disposition", "destination_path", "allocated_record_id",
    "source_sha256", "legacy_log_path", "legacy_event_ids", "legacy_ui_ids",
    "project_mapping", "metadata_mapping", "occurrence_source", "review_notes",
}

def validate(data):
    errors = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if not re.fullmatch(r"[0-9a-f]{40}", str(data.get("base_revision", ""))):
        errors.append("base_revision must be a full Git commit SHA")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return errors + ["items must be a nonempty array"]
    seen_sources, seen_destinations, seen_ids = set(), set(), set()
    for n, item in enumerate(items):
        prefix = f"items[{n}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        missing = REQUIRED - item.keys()
        if missing:
            errors.append(f"{prefix}: missing {sorted(missing)}")
            continue
        path = item["old_path"]
        if not isinstance(path, str) or not path.startswith("openwiki/") or not path.endswith(".md"):
            errors.append(f"{prefix}: invalid old_path")
        elif path in seen_sources:
            errors.append(f"{prefix}: duplicate source {path}")
        else:
            seen_sources.add(path)
        if item["disposition"] not in DISPOSITIONS:
            errors.append(f"{prefix}: unreviewed/invalid disposition")
        if not isinstance(item["source_sha256"], str) or not SHA256.fullmatch(item["source_sha256"]):
            errors.append(f"{prefix}: invalid source SHA-256")
        if not isinstance(item["review_notes"], str) or not item["review_notes"].strip() or "UNREVIEWED" in item["review_notes"].upper():
            errors.append(f"{prefix}: evidence-based review notes required")
        for field in ("legacy_event_ids", "legacy_ui_ids"):
            if not isinstance(item[field], list) or len(item[field]) != len(set(map(str, item[field]))):
                errors.append(f"{prefix}: invalid/duplicate {field}")
        if item["disposition"] in {"record", "summary-note"}:
            dest, rid = item["destination_path"], item["allocated_record_id"]
            if not isinstance(dest, str) or not dest.startswith("openwiki/") or not dest.endswith(".md") or "/../" in dest:
                errors.append(f"{prefix}: reviewed destination required")
            elif dest in seen_destinations:
                errors.append(f"{prefix}: destination collision {dest}")
            else:
                seen_destinations.add(dest)
            try:
                parsed = str(uuid.UUID(rid))
                if parsed != rid or rid in seen_ids:
                    raise ValueError("duplicate/noncanonical")
                seen_ids.add(rid)
            except (TypeError, ValueError, AttributeError):
                errors.append(f"{prefix}: unique canonical record UUID required")
            if not isinstance(item["metadata_mapping"], dict):
                errors.append(f"{prefix}: explicit metadata_mapping required")
            if not isinstance(item["project_mapping"], (dict, str)):
                errors.append(f"{prefix}: explicit project_mapping required")
        elif item["destination_path"] is not None or item["allocated_record_id"] is not None:
            errors.append(f"{prefix}: non-record disposition cannot allocate record/destination")
    if data.get("review_status") != "approved":
        errors.append("review_status must be approved after independent review")
    return errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=pathlib.Path)
    args = ap.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit(f"FAIL: cannot read manifest: {exc}")
    errors = validate(data)
    for error in errors:
        print("FAIL:", error)
    if errors:
        sys.exit(1)
    print(f"PASS: {len(data['items'])} reviewed manifest entries structurally valid")
    print("NOTE: content, snapshot, privacy and P10/P13/P15 evidence require separate checks")

if __name__ == "__main__":
    main()
