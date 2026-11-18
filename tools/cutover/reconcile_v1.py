"""M-04 no-loss reconciliation of a reviewed migration manifest against v1.

Pure, deterministic: the caller must supply original frozen bytes and archived
SHA-256s from the correct source repository, plus already validated native
records/histories. This does not replace the independent #36 rehearsal.
"""
from __future__ import annotations

import hashlib
from collections import Counter


class ReconciliationError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ReconciliationError(reason)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def reconcile(manifest, source_bytes, archived_hashes, records, histories):
    require(type(manifest) is dict and manifest.get("schema_version") == 1,
            "reviewed manifest schema required")
    require(manifest.get("review_status") == "reviewed-for-dry-run",
            "unreviewed source manifest")
    items = manifest.get("items")
    require(type(items) is list and items, "reviewed source inventory is empty")
    by_id = {r["id"]: r for r in records}
    require(len(by_id) == len(records), "duplicate current record IDs")
    events = {}
    for rid, history in histories.items():
        require(rid in by_id and history, "missing record for native history")
        for event in history:
            identifier = event["id"]
            require(identifier not in events, "duplicate native event allocation")
            events[identifier] = event
    seen_paths = set()
    matched_snapshots = 0
    archived = 0
    for item in items:
        old_path = item["old_path"]
        require(old_path not in seen_paths, "duplicate inventory source")
        seen_paths.add(old_path)
        original = source_bytes.get(old_path)
        require(type(original) is bytes, "frozen source missing: " + old_path)
        expected_hash = item["source_sha256"]
        require(sha256(original) == expected_hash,
                "reviewed frozen source digest mismatch: " + old_path)
        disposition = item["disposition"]
        if disposition in ("record", "summary-note"):
            rid = item["allocated_record_id"]
            require(rid in by_id and by_id[rid]["path"] == item["destination_path"],
                    "mapped canonical record missing: " + old_path)
            # Legacy snapshots are preserved as exact UTF-8 source strings.
            # This intentionally disallows fuzzy summary/title/date deduping.
            original_text = original.decode("utf-8", "strict")
            recorded = any(e.get("before") == original_text or
                           e.get("after") == original_text
                           for e in histories.get(rid, []))
            archived_copy = expected_hash in archived_hashes
            require(recorded or archived_copy,
                    "unique legacy source bytes lost: " + old_path)
            matched_snapshots += int(recorded)
            archived += int(archived_copy)
        elif disposition in ("duplicate-change", "structural"):
            require(expected_hash in archived_hashes,
                    "removed legacy evidence not archived: " + old_path)
            archived += 1
        else:
            raise ReconciliationError("unreviewed source disposition: " + old_path)

    def mapped_event(value, category, action=None):
        rid, eid = value["record_id"], value["allocated_event_id"]
        require(rid in histories, "unknown record for " + category)
        require(eid in events and events[eid]["record_id"] == rid,
                "missing allocated native " + category)
        event = events[eid]
        if action:
            require(event["action"] == action, category + " action mismatch")
        if "target_sequence" in value:
            require(event["sequence"] == value["target_sequence"],
                    category + " order/sequence mismatch")
        for key, target in (("allocated_operation_id", "operation_id"),
                            ("allocated_idempotency_key", "idempotency_key")):
            require(event[target] == value[key], category + " allocation mismatch")
        return event

    for mapping in manifest.get("legacy_event_mappings", []):
        event = mapped_event(mapping, "legacy-event")
        provenance = event["provenance"]
        require(provenance["kind"] == mapping["provenance_kind"] and
                provenance["source_ref"] == mapping["source_ref"] and
                provenance["original_time"] == mapping["original_time"],
                "legacy event provenance was lost")
    for mapping in manifest.get("normalization_event_allocations", []):
        mapped_event(mapping, "normalization", action="IMPORTED")
    for mapping in manifest.get("imported_baseline_allocations", []):
        event = mapped_event(mapping, "imported-baseline", action="IMPORTED")
        require(event["before"] is None, "imported baseline invents prior history")
    for mapping in manifest.get("legacy_ui_mappings", []):
        require(mapping["record_id"] in by_id, "legacy UI mapping lost record")
        eid = mapping.get("event_id")
        require(eid is None or eid in events, "legacy UI mapping lost event")

    return {
        "sources_checked": len(items),
        "records_mapped": sum(x["disposition"] in ("record", "summary-note") for x in items),
        "snapshots_matched": matched_snapshots,
        "archive_copies_verified": archived,
        "legacy_events_mapped": len(manifest.get("legacy_event_mappings", [])),
        "normalization_events_mapped": len(manifest.get("normalization_event_allocations", [])),
        "imported_baselines_mapped": len(manifest.get("imported_baseline_allocations", [])),
        "legacy_ui_aliases_checked": len(manifest.get("legacy_ui_mappings", [])),
        "native_current_records": len(records),
        "native_total_events": len(events),
    }
