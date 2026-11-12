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
