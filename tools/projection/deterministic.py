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
    """Write only to an isolated staging directory; caller owns atomic publication."""
    if destination.exists():
        raise ProjectionError("staging destination already exists")
    destination.mkdir(parents=True)
    for relative, content in sorted(files.items()):
        target = Path(relative)
        if target.is_absolute() or ".." in target.parts or not target.parts:
            raise ProjectionError("invalid output path")
        path = destination / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
