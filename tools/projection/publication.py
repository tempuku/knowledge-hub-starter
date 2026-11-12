"""Fail-closed publication allowlist validation for #32.

This module deliberately does not authorize a public build on its own.
The exporter must also enforce snapshot eligibility and audit output bytes.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from deterministic import ProjectionError, json_bytes

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
FIELDS = {"schema_version", "record_ids", "event_ids", "actor_labels"}


def validate_policy(raw: bytes) -> tuple[dict, str]:
    """Reject unknown fields, duplicates, wildcards, malformed IDs and unsorted lists."""
    try:
        policy = json.loads(raw, object_pairs_hook=_unique_pairs)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise ProjectionError("invalid publication policy JSON") from exc
    if not isinstance(policy, dict) or set(policy) != FIELDS or type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        raise ProjectionError("unknown or incomplete publication policy schema")
    for field in ("record_ids", "event_ids", "actor_labels"):
        values = policy[field]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v or v.strip() != v for v in values):
            raise ProjectionError("invalid publication allowlist")
        if values != sorted(set(values)):
            raise ProjectionError("allowlist must be unique and sorted")
        if any("*" in v or "?" in v for v in values):
            raise ProjectionError("wildcards are prohibited")
    for field in ("record_ids", "event_ids"):
        if any(UUID.fullmatch(v) is None for v in policy[field]):
            raise ProjectionError("invalid UUID in publication allowlist")
    if any(len(v) > 128 or any(ord(c) < 32 for c in v) for v in policy["actor_labels"]):
        raise ProjectionError("invalid actor label")
    return policy, hashlib.sha256(json_bytes(policy)).hexdigest()


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def load_policy(root: Path, mode: str, *, revision_bytes: bytes | None = None):
    """A public policy must be supplied from the same immutable revision as source.

    No working-tree fallback: caller must load the versioned policy via git show.
    """
    if mode != "public":
        raise ProjectionError("public policy loader only accepts explicit public mode")
    if revision_bytes is None:
        raise ProjectionError("missing immutable public policy")
    return validate_policy(revision_bytes)


def _visibility(snapshot: str | None) -> str | None:
    if snapshot is None:
        return None
    # Reuse canonical frontmatter parsing, never infer visibility from body text.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "records"))
    from validate_v1 import frontmatter
    try:
        metadata, _ = frontmatter(snapshot)
    except (ValueError, TypeError) as exc:
        raise ProjectionError("invalid publication snapshot") from exc
    value = metadata.get("visibility")
    if value not in ("public", "private"):
        raise ProjectionError("missing or invalid snapshot visibility")
    return value


def select_public(records: list[dict], histories: dict[str, list[dict]],
                  summaries: dict[str, dict], policy: dict):
    """Select current public records and explicitly approved public-only events.

    Never pass a private-before transition to the diff generator. A public
    record with no approved history remains visible with an empty history.
    """
    allowed_records = set(policy["record_ids"])
    allowed_events = set(policy["event_ids"])
    allowed_labels = set(policy["actor_labels"])
    chosen_records, chosen_histories, chosen_summaries = [], {}, {}
    for record in records:
        rid = record["id"]
        if rid not in allowed_records or _visibility(record["content"]) != "public":
            continue
        chosen_records.append(dict(record))
        selected = []
        for event in histories[rid]:
            if event["id"] not in allowed_events:
                continue
            if _visibility(event["after"]) != "public":
                continue
            if event["before"] is not None and _visibility(event["before"]) != "public":
                continue
            redacted = dict(event)
            redacted["actor"] = {
                "id": "redacted", "kind": event["actor"]["kind"],
                "label": event["actor"]["label"] if event["actor"]["label"] in allowed_labels else "Contributor",
            }
            # Internal provenance identifiers are never public metadata.
            redacted["provenance"] = {"kind": event["provenance"]["kind"],
                                      "source_ref": None, "original_time": None}
            # Internal command identifiers are not part of public provenance.
            redacted["idempotency_key"] = "redacted"
            redacted["request_sha256"] = "redacted"
            redacted["operation_id"] = "redacted"
            selected.append(redacted)
            summary = dict(summaries[event["id"]])
            summary["actor_label"] = redacted["actor"]["label"]
            summary["operation_id"] = "redacted"
            chosen_summaries[event["id"]] = summary
        chosen_histories[rid] = selected
    return chosen_records, chosen_histories, chosen_summaries


def audit_public(files: dict[str, bytes], forbidden: set[str]):
    """Byte-level denylist audit; run against every generated artifact.

    A denylist cannot establish that approved prose is safe: human review is
    still mandatory. Reject both direct UTF-8 and JSON-escaped occurrences.
    """
    for path, data in files.items():
        if not isinstance(data, bytes) or not path.endswith(".json"):
            raise ProjectionError("unexpected public artifact")
        for secret in forbidden:
            if not secret:
                continue
            variants = (secret.encode("utf-8"), json.dumps(secret, ensure_ascii=True)[1:-1].encode("utf-8"))
            if any(variant in data for variant in variants):
                raise ProjectionError(f"private reference detected in public artifact: {path}")
    return {"artifacts": sorted(files), "count": len(files)}
