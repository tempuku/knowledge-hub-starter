#!/usr/bin/env python3
"""Pure contract primitives for the v1 Knowledge Hub writer (DAG #28).

This module is intentionally not a second writable adapter. Git transactions,
locks, compare-and-swap publication and durable receipts must be implemented
and validated before any caller is permitted to invoke a write operation.
Existing legacy publish.py and journal behavior remain untouched.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import OrderedDict
from datetime import datetime, timezone

import yaml

from validate_v1 import (
    IntegrityError,
    digest,
    frontmatter,
    occurrence,
    parse_log,
    parse_record,
    safe_path,
    uid,
    validate_event,
    validate_meta,
)

COMMON = frozenset({
    "command", "idempotency_key", "actor", "summary", "expected_head",
    "occurred_on", "occurred_at", "publish_current",
})
FIELDS = {
    "create": frozenset({"path", "content"}),
    "update": frozenset({"record_id", "expected_version", "content"}),
}
SHA_HEAD = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
FENCE = chr(96) * 3
MAX_REQUEST_BYTES = 2 * 1024 * 1024


class WriterError(ValueError):
    """A transport-safe domain error, without private record snapshots."""

    def __init__(self, code, message, *, retryable=False, field_errors=None):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.field_errors = field_errors or []

    def response(self):
        return {
            "code": self.code,
            "message": str(self),
            "field_errors": self.field_errors,
            "retryable": self.retryable,
        }


def reject(code, message):
    raise WriterError(code, message)


def _no_floats(value):
    if isinstance(value, float):
        reject("VALIDATION_ERROR", "Floating point values are not allowed")
    if type(value) is dict:
        if any(type(k) is not str for k in value):
            reject("VALIDATION_ERROR", "JSON object keys must be strings")
        for inner in value.values():
            _no_floats(inner)
    elif type(value) is list:
        for inner in value:
            _no_floats(inner)


def normalized_request(request):
    """Strictly validate and expand only documented command defaults.

    The returned shape is safe to hash. Authorization/capability context is
    intentionally supplied by the trusted adapter, not the request body.
    """
    if type(request) is not dict:
        reject("VALIDATION_ERROR", "Request must be a JSON object")
    _no_floats(request)
    try:
        encoded = json.dumps(request, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        reject("VALIDATION_ERROR", "Request must be UTF-8 JSON compatible")
    if len(encoded) > MAX_REQUEST_BYTES:
        reject("VALIDATION_ERROR", "Request exceeds 2 MiB")
    command = request.get("command")
    if command not in FIELDS:
        reject("VALIDATION_ERROR", "Unsupported writer command")
    unknown = set(request) - COMMON - FIELDS[command]
    if unknown:
        reject("VALIDATION_ERROR", "Unknown request fields")
    required = {"command", "idempotency_key", "actor", "summary",
                "expected_head", "content"} | (
                    {"path"} if command == "create" else
                    {"record_id", "expected_version"}
                )
    if required - set(request):
        reject("VALIDATION_ERROR", "Missing required request fields")
    try:
        uid(request["idempotency_key"], "idempotency_key")
        if command == "create":
            safe_path(request["path"], "path")
        else:
            uid(request["record_id"], "record_id")
            uid(request["expected_version"], "expected_version")
        if type(request["expected_head"]) is not str or not SHA_HEAD.fullmatch(
            request["expected_head"]
        ):
            raise IntegrityError("expected_head must be a full Git commit SHA")
        if type(request["content"]) is not str:
            raise IntegrityError("content must be a string")
        if len(request["content"].encode("utf-8")) > 1048576:
            raise IntegrityError("record content exceeds 1 MiB")
        actor = request["actor"]
        if type(actor) is not dict or set(actor) != {"id", "kind", "label"}:
            raise IntegrityError("actor must provide id, kind and label")
        for name, limit in (("id", 200), ("label", 100)):
            value = actor[name]
            if (type(value) is not str or not 1 <= len(value) <= limit or
                    value != value.strip() or any(x in value for x in "\n\r\0")):
                raise IntegrityError("invalid actor " + name)
        if actor["kind"] not in ("human", "agent", "migration"):
            raise IntegrityError("invalid actor kind")
        summary = request["summary"]
        if (type(summary) is not str or not 1 <= len(summary) <= 240 or
                summary != summary.strip() or any(x in summary for x in "\r\n\0")):
            raise IntegrityError("invalid summary")
        if "publish_current" in request and type(request["publish_current"]) is not bool:
            raise IntegrityError("publish_current must be boolean")
        occurrence(request.get("occurred_on"), request.get("occurred_at"), "request")
    except (IntegrityError, UnicodeError) as exc:
        reject("VALIDATION_ERROR", str(exc))
    result = {k: request.get(k) for k in COMMON | FIELDS[command]}
    result["publish_current"] = request.get("publish_current", False)
    return result


def request_digest(normalized):
    """W-02 SHA-256 over canonical JSON, excluding idempotency key."""
    payload = {k: v for k, v in normalized.items() if k != "idempotency_key"}
    _no_floats(payload)
    serial = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                        separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serial.encode("utf-8")).hexdigest()


class _QuotedDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

    def represent_mapping(self, tag, mapping, flow_style=None):
        node = super().represent_mapping(tag, mapping, flow_style)
        # The v1 repository scanner recognizes unquoted id/schema_version keys.
        for key_node, _ in node.value:
            if (isinstance(key_node, yaml.ScalarNode) and
                    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key_node.value)):
                key_node.style = None
        return node


def _quoted_str(dumper, data):
    # Quoting every string value also avoids YAML 1.1 booleans and date coercion.
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


_QuotedDumper.add_representer(str, _quoted_str)


def create_source(content, record_id):
    """Generate a canonical v1 record from create input without generated IDs."""
    try:
        uid(record_id, "record_id")
        meta, body = frontmatter(content)
        if "id" in meta or "schema_version" in meta:
            raise IntegrityError("create input must not provide generated fields")
        ordered = OrderedDict()
        ordered["id"] = record_id
        ordered["schema_version"] = 1
        for name in ("type", "title", "description", "status", "visibility",
                     "project_id", "tags", "occurred_on", "occurred_at",
                     "reminders", "sources"):
            if name in meta:
                ordered[name] = meta[name]
            elif name == "status":
                ordered[name] = "draft"
            elif name == "visibility":
                ordered[name] = "private"
        for name in sorted(k for k in meta if k.startswith("x_")):
            ordered[name] = meta[name]
        validate_meta(dict(ordered), body, "new record")
        # Dict preserves insertion order and PyYAML emits two-space block nesting.
        yaml_body = yaml.dump(dict(ordered), Dumper=_QuotedDumper,
                              sort_keys=False, allow_unicode=True,
                              default_flow_style=False, indent=2)
        result = "---\n" + yaml_body + "---\n" + body
        parse_record(result.encode("utf-8"), "new record")
        return result
    except (IntegrityError, yaml.YAMLError, UnicodeError) as exc:
        reject("VALIDATION_ERROR", str(exc))


def make_event(normalized, *, record_id, event_id, operation_id,
               sequence, action, path_before, path_after,
               before, after, previous_event_id, recorded_at=None):
    """Build one immutable event; caller owns authorization and transaction."""
    timestamp = recorded_at or datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")
    event = {
        "schema_version": 1,
        "id": event_id,
        "record_id": record_id,
        "operation_id": operation_id,
        "sequence": sequence,
        "action": action,
        "recorded_at": timestamp,
        "occurred_on": normalized["occurred_on"],
        "occurred_at": normalized["occurred_at"],
        "actor": normalized["actor"],
        "summary": normalized["summary"],
        "path_before": path_before,
        "path_after": path_after,
        "before": before,
        "after": after,
        "before_sha256": digest(before) if before is not None else None,
        "after_sha256": digest(after),
        "previous_event_id": previous_event_id,
        "idempotency_key": normalized["idempotency_key"],
        "request_sha256": request_digest(normalized),
        "provenance": {"kind": "native", "source_ref": None, "original_time": None},
    }
    try:
        validate_event(event, "writer event")
    except IntegrityError as exc:
        reject("VALIDATION_ERROR", str(exc))
    return event


def append_log(log_text, event):
    """Append one exact canonical JSON event; no historical byte rewriting."""
    section = ("## Entry " + event["id"] + "\n" + FENCE + "json\n" +
               json.dumps(event, ensure_ascii=False, indent=2) +
               "\n" + FENCE + "\n")
    text = ("# Record history\n\n" if log_text is None else log_text + "\n") + section
    try:
        parsed = parse_log(text.encode("utf-8"), "new log")
        if parsed[-1] != event:
            raise IntegrityError("last event differs from appended entry")
    except IntegrityError as exc:
        reject("INTEGRITY_ERROR", str(exc))
    return text


def receipt_from_logs(logs, normalized):
    """Recover a durable operation receipt from canonical committed logs.

    logs maps current sibling paths to exact UTF-8 bytes, read from a trusted
    committed Git tree. Call this *before* stale-head or no-change validation.
    A shared operation may produce multiple events in the move phase; this
    create/update slice rejects ambiguous multi-record receipts.
    """
    key = normalized["idempotency_key"]
    expected = request_digest(normalized)
    matches = []
    for path, source in logs.items():
        try:
            events = parse_log(source, path)
        except (IntegrityError, UnicodeError) as exc:
            reject("INTEGRITY_ERROR", "Cannot read committed record history: " + str(exc))
        for event in events:
            if event["idempotency_key"] == key:
                try:
                    validate_event(event, path)
                except IntegrityError as exc:
                    reject("INTEGRITY_ERROR", str(exc))
                if event["request_sha256"] != expected:
                    reject("IDEMPOTENCY_CONFLICT",
                           "Idempotency key was committed with different request fields")
                matches.append(event)
    if not matches:
        return None
    operation_ids = {e["operation_id"] for e in matches}
    if len(operation_ids) != 1:
        reject("INTEGRITY_ERROR", "One idempotency key maps to multiple operations")
    if len(matches) != 1:
        reject("INTEGRITY_ERROR", "Multiple-record receipt requires move transaction handler")
    return matches[0]


def require_capability(normalized, capability):
    """Enforce trusted adapter capabilities; never trust flags in caller JSON.

    A public repository cannot contain private snapshots, even when a caller
    requests publication. A future publishing allowlist is a separate concern.
    """
    if type(capability) is not dict or set(capability) != {
        "repository_mode", "operations", "publisher_scope"
    }:
        reject("PUBLICATION_DENIED", "Trusted repository capability is unavailable")
    mode = capability["repository_mode"]
    operations = capability["operations"]
    if mode not in ("public", "private") or type(operations) not in (list, tuple, set):
        reject("PUBLICATION_DENIED", "Trusted repository capability is invalid")
    if normalized["command"] not in operations:
        reject("PUBLICATION_DENIED", "Operation not permitted by trusted adapter")
    if type(capability["publisher_scope"]) is not bool:
        reject("PUBLICATION_DENIED", "Publisher authorization is invalid")
    if normalized["publish_current"] and not capability["publisher_scope"]:
        reject("PUBLICATION_DENIED", "Publisher scope is required")
    if mode == "public":
        # Even explicit publish_current cannot authorize exposing prior
        # private history. Only already-public snapshots can be written.
        if normalized["command"] == "create":
            meta, _ = frontmatter(normalized["content"])
            if meta.get("visibility", "private") != "public":
                reject("PUBLICATION_DENIED", "Private records cannot enter a public Git repository")
            if not normalized["publish_current"]:
                reject("PUBLICATION_DENIED", "Explicit publication is required in a public repository")
        else:
            meta, _ = frontmatter(normalized["content"])
            if meta.get("visibility") != "public":
                reject("PUBLICATION_DENIED", "Private records cannot enter a public Git repository")
    return True
