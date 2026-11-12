"""Deterministic P-02 event, history and diary read-model construction.

Pure in-memory projection. No publication or production-builder side effects.
"""
from __future__ import annotations

import difflib
from collections import defaultdict
from datetime import datetime, timezone

from deterministic import ProjectionError, json_bytes, paginate


def utc_day(timestamp: str) -> str:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("missing timezone")
        return parsed.astimezone(timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProjectionError("invalid recorded_at timestamp") from exc


def event_detail(event: dict) -> dict:
    before = event["before"] or ""
    after = event["after"]
    if not isinstance(after, str) or not isinstance(before, str):
        raise ProjectionError("invalid event snapshots")
    diff = "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="before", tofile="after", n=3,
    ))
    return {"schema_version": 1, "event": event,
            "revision_metadata": {"record_id": event["record_id"],
                                  "sequence": event["sequence"],
                                  "path_before": event["path_before"],
                                  "path_after": event["path_after"]},
            "diff": {"format": "unified", "context_lines": 3, "text": diff}}


def build_event_pages(histories: dict[str, list[dict]], summaries: dict[str, dict]) -> dict[str, bytes]:
    """Build immutable event details, per-record history and UTC Diary pages.

    The caller must supply validated eligible events and snapshot-derived
    summaries. Missing summaries, duplicate IDs or mismatched record IDs fail.
    """
    files: dict[str, bytes] = {}
    days = defaultdict(list)
    months = defaultdict(list)
    calendar = defaultdict(list)
    seen = set()
    for rid, events in sorted(histories.items()):
        for event in events:
            eid = event["id"]
            if eid in seen or event["record_id"] != rid or eid not in summaries:
                raise ProjectionError("duplicate, mismatched or unsummarized event")
            seen.add(eid)
            detail = event_detail(event)
            raw = json_bytes(detail)
            summary = dict(summaries[eid])
            if summary["id"] != eid or summary["record_id"] != rid:
                raise ProjectionError("summary identity mismatch")
            summary["detail_bytes"] = len(raw)
            files[f"events/{eid}.json"] = raw
            files[f"events/{eid}.meta.json"] = json_bytes({"schema_version": 1, **summary})
            days[utc_day(event["recorded_at"])].append(summary)
        ordered = sorted((dict(summaries[e["id"]], detail_bytes=len(files[f'events/{e["id"]}.json']))
                          for e in events), key=lambda x: x["sequence"], reverse=True)
        pages = paginate(ordered, event_summaries=True)
        descriptors = []
        for i, page in enumerate(pages, 1):
            path = f"history/{rid}/{i}.json"
            files[path] = page
            descriptors.append({"number": i, "url": path, "count": len(__import__("json").loads(page)["items"])})
        files[f"history/{rid}/index.json"] = json_bytes({
            "schema_version": 1, "record_id": rid, "event_count": len(events), "pages": descriptors})
    for day, items in sorted(days.items(), reverse=True):
        items.sort(key=lambda x: (x["recorded_at"], x["sequence"], x["id"]), reverse=True)
        pages = paginate(items, event_summaries=True)
        descriptors = []
        for i, page in enumerate(pages, 1):
            path = f"days/{day}/{i}.json"
            files[path] = page
            descriptors.append({"number": i, "url": path, "count": len(__import__("json").loads(page)["items"])})
        files[f"days/{day}/index.json"] = json_bytes({
            "schema_version": 1, "date": day, "change_count": len(items),
            "record_count": len({x["record_id"] for x in items}), "pages": descriptors})
        months[day[:7]].extend(items)
        calendar[day[:4]].append({"date": day, "change_count": len(items),
                                  "record_count": len({x["record_id"] for x in items})})
    for year, dates in sorted(calendar.items()):
        files[f"calendar/{year}.json"] = json_bytes({
            "schema_version": 1, "year": int(year), "days": dates})
    files["event-counts.json"] = json_bytes({
        "schema_version": 1, "event_count": len(seen),
        "months": [{"month": month, "change_count": len(items),
                    "record_count": len({x["record_id"] for x in items})}
                   for month, items in sorted(months.items(), reverse=True)]})
    return files
