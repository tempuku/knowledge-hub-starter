"""Deterministic primitives for the target native-log read-model builder (#31).

This module does not publish or replace the legacy builder.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

SCHEMA_VERSION = 1
PAGE_LIMIT = 50
PAGE_BYTES = 128 * 1024
EVENT_SUMMARY_LIMIT = 16 * 1024
SEARCH_SHARD_LIMIT = 512 * 1024
TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
FIELD_WEIGHTS = {"title": 8, "tag": 4, "description": 2, "body": 1}


class ProjectionError(ValueError):
    """Invalid source or projection budget; publication must fail closed."""


def json_bytes(payload: dict) -> bytes:
    """Canonical output JSON: UTF-8, two-space indentation and trailing LF."""
    return (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def generation_id(source_tree_hash: str, exporter_version: str, policy_digest: str) -> str:
    material = "\n".join((source_tree_hash, exporter_version, policy_digest))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def tokenize(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", value).lower()
    return [token for token in TOKEN_PATTERN.findall(normalized) if 2 <= len(token) <= 64]


def search_shards(records: list[dict]) -> dict[str, bytes]:
    """Create a deterministic token -> record/field inverted index."""
    shards = defaultdict(lambda: defaultdict(dict))
    for record in sorted(records, key=lambda item: item["id"]):
        rid = record["id"]
        fields = {
            "title": record.get("title", ""),
            "description": record.get("description", ""),
            "tag": " ".join(record.get("tags", [])),
            "body": record.get("body", ""),
        }
        for field, value in fields.items():
            for token in set(tokenize(value)):
                prefix = hashlib.sha256(token.encode("utf-8")).hexdigest()[:2]
                shards[prefix][token].setdefault(rid, set()).add(field)
    output = {}
    for prefix, terms in sorted(shards.items()):
        encoded = json_bytes({
            "schema_version": SCHEMA_VERSION,
            "terms": {
                token: [
                    {"record_id": rid, "fields": sorted(fields)}
                    for rid, fields in sorted(postings.items())
                ]
                for token, postings in sorted(terms.items())
            },
        })
        if len(encoded) > SEARCH_SHARD_LIMIT:
            raise ProjectionError(f"search shard {prefix} exceeds 512 KiB")
        output[prefix] = encoded
    return output


def paginate(items: list[dict], *, event_summaries: bool = False) -> list[bytes]:
    """Split before exceeding 50 items or 128 KiB; never silently truncate."""
    pages = []
    current = []
    for item in items:
        if event_summaries and len(json_bytes(item)) > EVENT_SUMMARY_LIMIT:
            raise ProjectionError("event summary exceeds 16 KiB")
        candidate = current + [item]
        if current and (len(candidate) > PAGE_LIMIT or
                        len(json_bytes({"schema_version": 1, "items": candidate, "next": None})) > PAGE_BYTES):
            pages.append(current)
            current = [item]
        else:
            current = candidate
        if len(json_bytes({"schema_version": 1, "items": current, "next": None})) > PAGE_BYTES:
            raise ProjectionError("single item exceeds page budget")
    if current:
        pages.append(current)
    return [
        json_bytes({"schema_version": 1, "items": page,
                    "next": index + 2 if index + 1 < len(pages) else None})
        for index, page in enumerate(pages)
    ]


def write_staging(destination: Path, files: dict[str, bytes]) -> None:
    """Stage validated files without publishing partial output on failure.

    Reject unsafe paths and collisions before touching the filesystem. On an I/O
    failure remove the incomplete staging tree; the caller's published generation
    and manifest are never modified.
    """
    import shutil

    if destination.exists() or destination.is_symlink():
        raise ProjectionError("staging destination already exists")
    validated = []
    seen = set()
    for relative, content in sorted(files.items()):
        if not isinstance(relative, str) or not relative or not isinstance(content, bytes):
            raise ProjectionError("invalid staging entry")
        target = Path(relative)
        if (target.is_absolute() or "\\\\" in relative or
                any(part in ("", ".", "..") for part in relative.split("/")) or
                target.as_posix() != relative):
            raise ProjectionError("invalid output path")
        key = relative.casefold()
        if key in seen:
            raise ProjectionError("case-insensitive output path collision")
        seen.add(key)
        validated.append((target, content))
    for target, _ in validated:
        for parent in target.parents:
            if parent == Path("."):
                break
            if parent.as_posix().casefold() in seen:
                raise ProjectionError("output path conflicts with a file")
    try:
        destination.mkdir(parents=True)
        for target, content in validated:
            path = destination / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    except Exception:
        if destination.is_dir():
            shutil.rmtree(destination)
        raise


def query_search(query: str, records: list[dict], shards: dict[str, bytes],
                 *, project_id: str | None = None, area: str | None = None,
                 record_type: str | None = None, status: str | None = None,
                 tag: str | None = None, include_archived: bool = False) -> list[str]:
    """Return matching IDs ordered by P-03 ranking and deterministic tie breaks.

    Filters apply to eligible current metadata, never to historical snapshots.
    """
    tokens = list(dict.fromkeys(tokenize(query)))
    if len(tokens) > 8:
        raise ProjectionError("query exceeds eight distinct tokens")
    by_id = {record["id"]: record for record in records}
    scores = defaultdict(int)
    matches = None
    for token in tokens:
        prefix = hashlib.sha256(token.encode("utf-8")).hexdigest()[:2]
        payload = json.loads(shards.get(prefix, json_bytes({"schema_version": 1, "terms": {}})))
        postings = payload["terms"].get(token, [])
        current = set()
        for posting in postings:
            rid = posting["record_id"]
            if rid not in by_id:
                raise ProjectionError("search references unknown record")
            current.add(rid)
            scores[rid] += max(FIELD_WEIGHTS[field] for field in posting["fields"])
        matches = current if matches is None else matches & current
        if not matches:
            return []
    candidates = matches if matches is not None else set(by_id)
    result = []
    for rid in candidates:
        record = by_id[rid]
        if record.get("status") == "deprecated" and not (
                include_archived or status == "deprecated"):
            continue
        if project_id is not None and record.get("project_id") != project_id:
            continue
        record_area = record.get("area", "")
        if area is not None and not (record_area == area or record_area.startswith(area.rstrip("/") + "/")):
            continue
        if record_type is not None and record.get("type") != record_type:
            continue
        if status is not None and record.get("status") != status:
            continue
        if tag is not None and tag not in record.get("tags", []):
            continue
        result.append(rid)
    # Stable sorts implement descending score, descending timestamp, ascending ID.
    result.sort()
    result.sort(key=lambda rid: by_id[rid].get("updated_at", ""), reverse=True)
    result.sort(key=lambda rid: scores[rid], reverse=True)
    return result
