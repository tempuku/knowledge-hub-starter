"""Compose validated eligible v1 records and native histories into P-02 JSON.

Caller supplies immutable-revision records and histories; publishing and public
allowlisting are deliberately separate operations.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json

from deterministic import ProjectionError, json_bytes, search_shards
from event_pages import build_event_pages
from record_pages import build_record_pages
from reminders import project_reminders


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
    files = build_record_pages(records)
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
        aliases = {"paths": {}, "entries": {}}
    if set(aliases) != {"paths", "entries"}:
        raise ProjectionError("invalid alias structure")
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
