#!/usr/bin/env python3
"""Trusted launch boundary for one v1 Knowledge Hub domain writer.

Both the CLI and local MCP stdio use this module, never the legacy journal
publisher. No remote identity is verified: event actors are caller-supplied
provenance. Capability configuration is an external trusted launch file, not
part of the JSON-RPC or CLI command request.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RECORDS = Path(__file__).resolve().parents[1] / "records"
if str(RECORDS) not in sys.path:
    sys.path.insert(0, str(RECORDS))

from service_v1 import GitRecordWriter
from writer_v1 import WriterError

MAX_CONFIG_BYTES = 16384
MAX_REQUEST_BYTES = 2 * 1024 * 1024
COMMANDS = frozenset({"read", "create", "update", "move", "archive", "reopen"})


def _unique_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON property")
        result[name] = value
    return result


def decode_json(source, *, maximum):
    if type(source) is not bytes or len(source) > maximum:
        raise WriterError("VALIDATION_ERROR", "JSON input exceeds permitted size")
    try:
        return json.loads(source.decode("utf-8", "strict"),
                          object_pairs_hook=_unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              ValueError("Invalid JSON constant")))
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise WriterError("VALIDATION_ERROR", "Malformed UTF-8 JSON input") from exc


def load_capability(root, capability_file):
    """Do not trust caller JSON as authorization or infer public repo mode."""
    root = Path(root).resolve(strict=True)
    cap_path = Path(capability_file)
    if cap_path.is_symlink() or not cap_path.is_file():
        raise WriterError("PUBLICATION_DENIED", "Trusted capability file unavailable")
    cap_path = cap_path.resolve(strict=True)
    if cap_path == root or root in cap_path.parents:
        raise WriterError("PUBLICATION_DENIED",
                          "Capability file must be outside the repository")
    obj = decode_json(cap_path.read_bytes(), maximum=MAX_CONFIG_BYTES)
    if type(obj) is not dict or set(obj) - {
        "repository_mode", "operations", "publisher_scope", "writable_record_ids"
    } or not {"repository_mode", "operations", "publisher_scope"} <= set(obj):
        raise WriterError("PUBLICATION_DENIED", "Invalid trusted capability configuration")
    if (obj["repository_mode"] not in ("public", "private") or
            type(obj["operations"]) is not list or
            not obj["operations"] or
            any(type(x) is not str or x not in COMMANDS for x in obj["operations"]) or
            len(set(obj["operations"])) != len(obj["operations"]) or
            type(obj["publisher_scope"]) is not bool):
        raise WriterError("PUBLICATION_DENIED", "Invalid trusted capability configuration")
    if "writable_record_ids" in obj and (
            type(obj["writable_record_ids"]) is not list or
            any(type(x) is not str for x in obj["writable_record_ids"])):
        raise WriterError("PUBLICATION_DENIED", "Invalid per-record capability configuration")
    return obj


def staged_okf(workspace):
    """Run the pinned staged OpenWiki checker on real isolated staged files."""
    checker = Path(__file__).resolve().parents[1] / "okf" / "verify.mjs"
    if not checker.is_file():
        raise WriterError("WRITE_FAILED", "Trusted staged checker missing")
    result = subprocess.run(["node", str(checker)], cwd=workspace,
                            capture_output=True)
    if result.returncode:
        raise WriterError("INTEGRITY_ERROR", "Staged OKF validation failed")


def new_writer(*, root, capability_file, branch="main", remote=None):
    if not isinstance(branch, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch) or ".." in branch:
        raise WriterError("VALIDATION_ERROR", "Invalid configured branch")
    repo = Path(root).resolve(strict=True)
    if not (repo / ".git").exists():
        raise WriterError("WRITE_FAILED", "Trusted checkout must be a Git repository")
    capability = load_capability(repo, capability_file)
    return GitRecordWriter(repo, capability, branch=branch, remote=remote,
                           staged_checker=staged_okf)


def execute(writer, request):
    """One business operation implementation shared by both transports."""
    if type(request) is not dict:
        raise WriterError("VALIDATION_ERROR", "Command must be JSON object")
    command = request.get("command")
    if command == "read":
        if set(request) != {"command", "record_id"}:
            raise WriterError("VALIDATION_ERROR", "Invalid read request fields")
        return writer.read(request["record_id"])
    if command not in COMMANDS:
        raise WriterError("VALIDATION_ERROR", "Unsupported knowledge command")
    try:
        return writer.write(request)
    except WriterError:
        raise
    except Exception as exc:
        # The response must not leak private record snapshots or filesystem paths.
        raise WriterError("WRITE_FAILED",
                          "Writer outcome uncertain; retry the same idempotency key",
                          retryable=True) from exc
