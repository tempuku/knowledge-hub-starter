"""Compose validated eligible v1 records and native histories into P-02 JSON.

Caller supplies immutable-revision records and histories; publishing and public
allowlisting are deliberately separate operations.
"""
from __future__ import annotations

from collections import Counter
import json
import re

from deterministic import ProjectionError, json_bytes, search_shards
from event_pages import build_event_pages
from record_pages import build_record_pages
from reminders import project_reminders

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _validated_aliases(aliases: dict, record_ids: set[str], event_ids: set[str]) -> dict:
    if not isinstance(aliases, dict) or not (
            set(aliases) == {"paths", "entries"} or
            set(aliases) == {"paths", "entries", "current_entries"}):
        raise ProjectionError("invalid alias structure")
    paths, entries = aliases["paths"], aliases["entries"]
    current_entries = aliases.get("current_entries", {})
    if not isinstance(paths, dict) or not isinstance(entries, dict) or not isinstance(current_entries, dict):
        raise ProjectionError("invalid alias maps")
    clean_paths = {}
    for path, ids in paths.items():
        if (not isinstance(path, str) or not path.startswith("openwiki/") or
                len(path.encode("utf-8")) > 240 or not path.endswith(".md") or
                "\\" in path or "\0" in path or
                any(ord(char) < 32 or ord(char) == 127 for char in path) or
                any(part in ("", ".", "..") for part in path.split("/")) or
                not isinstance(ids, list) or not ids or
                any(not isinstance(rid, str) or not UUID.fullmatch(rid) or rid not in record_ids
                    for rid in ids) or ids != sorted(set(ids))):
            raise ProjectionError("invalid path alias")
        clean_paths[path] = ids
    clean_entries = {}
    for legacy_id, event_id in entries.items():
        if (not isinstance(legacy_id, str) or not legacy_id or len(legacy_id) > 1024 or
                any(ord(c) < 32 or ord(c) == 127 for c in legacy_id) or not isinstance(event_id, str) or
                event_id not in event_ids):
            raise ProjectionError("invalid legacy entry alias")
        clean_entries[legacy_id] = event_id
    clean_current = {}
    for legacy_id, record_id in current_entries.items():
        if (not isinstance(legacy_id, str) or not legacy_id or len(legacy_id) > 1024 or
                any(ord(c) < 32 or ord(c) == 127 for c in legacy_id) or
                not isinstance(record_id, str) or record_id not in record_ids or
                legacy_id in clean_entries):
            raise ProjectionError("invalid legacy current-record alias")
        clean_current[legacy_id] = record_id
    result = {"paths": dict(sorted(clean_paths.items())),
              "entries": dict(sorted(clean_entries.items()))}
    if "current_entries" in aliases:
        result["current_entries"] = dict(sorted(clean_current.items()))
    return result


def build_projection(records: list[dict], histories: dict[str, list[dict]],
                     summaries: dict[str, dict],
                     *, aliases: dict | None = None) -> dict[str, bytes]:
    """Build an in-memory generation; reject incomplete inputs before publication."""
    by_id = {r["id"]: r for r in records}
    if len(by_id) != len(records):
        raise ProjectionError("duplicate canonical record ID")
    if set(histories) != set(by_id):
        raise ProjectionError("canonical/history record sets differ")
    expected_events = {e["id"] for events in histories.values() for e in events}
    if len(expected_events) != sum(map(len, histories.values())) or set(summaries) != expected_events:
        raise ProjectionError("event summary set mismatch")
    # Backlinks are a read model: compute solely from visible, validated outgoing
    # links after publication filtering. Never copy the source's private identity
    # or content into a public destination, and never write a backlink to source.
    incoming = {rid: [] for rid in by_id}
    for source in records:
        seen = set()
        for edge in source.get("links", []):
            if not isinstance(edge, dict):
                raise ProjectionError("invalid canonical link metadata")
            target_id = edge.get("target_id")
            if (edge.get("available") is False or target_id not in by_id or
                    target_id == source["id"] or target_id in seen):
                continue
            seen.add(target_id)
            incoming[target_id].append({"source_id": source["id"], "title": source["title"]})
    with_backlinks = [
        {**record, "backlinks": sorted(incoming[record["id"]],
          key=lambda link: (link["title"].casefold(), link["source_id"]))}
        for record in records
    ]
    files = build_record_pages(with_backlinks)
    for path, content in build_event_pages(histories, summaries).items():
        if path in files:
            raise ProjectionError("projection output path collision")
        files[path] = content
    for month, payload in project_reminders(records).items():
        files[f"reminders/{month}.json"] = json_bytes(payload)
    shards = search_shards(records)
    files["search/manifest.json"] = json_bytes({
        "schema_version": 1,
        "shards": [{"prefix": prefix, "url": f"search/{prefix}.json"}
                   for prefix in sorted(shards)],
        "record_count": len(records)})
    for prefix, payload in shards.items():
        files[f"search/{prefix}.json"] = payload
    if aliases is None:
        from git_source import derive_aliases
        aliases = derive_aliases(records, histories)
    aliases = _validated_aliases(aliases, set(by_id), expected_events)
    files["aliases.json"] = json_bytes({"schema_version": 1, **aliases})
    areas = Counter(r["area"] for r in records)
    projects = sorted(
        ({"id": r["id"], "title": r["title"]}
         for r in records if r["type"] == "project"),
        key=lambda x: (x["title"].casefold(), x["id"]))
    counts = json.loads(files.pop("event-counts.json"))
    files["catalog.json"] = json_bytes({
        "schema_version": 1, "record_count": len(records),
        "event_count": len(expected_events), "projects": projects,
        "areas": [{"path": area, "count": count} for area, count in sorted(areas.items())],
        "months": counts["months"]})
    return dict(sorted(files.items()))
