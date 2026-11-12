"""Strict native S-03 log reader for the #31 read-model pipeline.

Read-only: never modifies canonical records, logs or the production exporter.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from deterministic import ProjectionError

HEADER = "# Record history\n"
ENTRY = re.compile(r"## Entry ([0-9a-f-]{36})\n\x60\x60\x60json\n(.*?)\n\x60\x60\x60\n", re.DOTALL)
UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
REQUIRED = frozenset((
    "schema_version", "id", "record_id", "operation_id", "sequence", "action",
    "recorded_at", "occurred_on", "occurred_at", "actor", "summary",
    "path_before", "path_after", "before", "after", "before_sha256",
    "after_sha256", "previous_event_id", "idempotency_key", "request_sha256",
    "provenance",
))
ACTIONS = {"CREATED", "UPDATED", "MOVED", "ARCHIVED", "REOPENED", "IMPORTED"}


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProjectionError("duplicate JSON key")
        result[key] = value
    return result


def _hash(snapshot):
    return None if snapshot is None else hashlib.sha256(snapshot.encode("utf-8")).hexdigest()


def parse_log(text: str, *, canonical: str | None = None,
              canonical_path: str | None = None) -> list[dict]:
    """Consume an entire native log and verify contiguous snapshot history.

    A source tree validator remains responsible for full S-02 schema checks,
    global UUID uniqueness, provenance and trusted Git-prefix validation.
    """
    if not text.startswith(HEADER) or "\r" in text or not text.endswith("\n"):
        raise ProjectionError("invalid native log header or encoding")
    position = len(HEADER)
    events = []
    while position < len(text):
        if text[position] == "\n":
            position += 1
            continue
        match = ENTRY.match(text, position)
        if match is None:
            raise ProjectionError("unmatched text or malformed native log entry")
        position = match.end()
        try:
            event = json.loads(match.group(2), object_pairs_hook=_unique_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ProjectionError("nonfinite JSON")))
        except (ValueError, TypeError) as exc:
            raise ProjectionError("invalid event JSON") from exc
        if not isinstance(event, dict) or set(event) != REQUIRED:
            raise ProjectionError("invalid event key set")
        if event["schema_version"] != 1 or type(event["sequence"]) is not int:
            raise ProjectionError("invalid event version or sequence")
        if event["id"] != match.group(1) or not UUID4.fullmatch(event["id"]):
            raise ProjectionError("entry ID mismatch")
        if any(not isinstance(event[k], str) or not UUID4.fullmatch(event[k])
               for k in ("record_id", "operation_id", "idempotency_key")):
            raise ProjectionError("invalid event identity")
        if event["action"] not in ACTIONS:
            raise ProjectionError("unknown event action")
        if not isinstance(event["after"], str) or not isinstance(event["path_after"], str):
            raise ProjectionError("missing after snapshot or path")
        if event["after_sha256"] != _hash(event["after"]) or event["before_sha256"] != _hash(event["before"]):
            raise ProjectionError("snapshot digest mismatch")
        if events:
            previous = events[-1]
            if (event["record_id"] != previous["record_id"] or
                    event["sequence"] != previous["sequence"] + 1 or
                    event["previous_event_id"] != previous["id"] or
                    event["before"] != previous["after"] or
                    event["path_before"] != previous["path_after"] or
                    event["recorded_at"] < previous["recorded_at"]):
                raise ProjectionError("broken native log chain")
        elif (event["sequence"] != 1 or event["previous_event_id"] is not None or
              event["before"] is not None or event["path_before"] is not None):
            raise ProjectionError("invalid first event")
        events.append(event)
    if not events:
        raise ProjectionError("empty native log")
    if canonical is not None and events[-1]["after"] != canonical:
        raise ProjectionError("final snapshot differs from canonical record")
    if canonical_path is not None and events[-1]["path_after"] != canonical_path:
        raise ProjectionError("final path differs from canonical record")
    return events


def read_log(path: Path, **kwargs) -> list[dict]:
    try:
        text = path.read_bytes().decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ProjectionError("native log is not UTF-8") from exc
    return parse_log(text, **kwargs)
