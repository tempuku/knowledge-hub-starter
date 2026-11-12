#!/usr/bin/env python3
"""Local stdio MCP server, six tools backed by the same v1 Knowledge Hub writer.

Standard MCP stdio framing is one UTF-8 JSON-RPC object per newline, NOT
HTTP Content-Length headers. A server is launched by a trusted local client
with an external authorization profile; no network listener, verified remote
identity or unauthenticated HTTP endpoint exists.

Actor metadata inside tool arguments is SUPPLIED provenance, not attested.
"""
from __future__ import annotations

import argparse
import json
import sys

from knowledge_service import (MAX_REQUEST_BYTES, WriterError,
                               decode_json, execute, new_writer)

MAX_MESSAGE = MAX_REQUEST_BYTES + 8192
SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-11-25", "2026-07-28"}
ERRORS = {
    -32700: "Parse error",
    -32600: "Invalid Request",
    -32601: "Method not found",
    -32602: "Invalid params",
    -32603: "Internal error",
}
ACTOR = {
    "type": "object", "properties": {
        "id": {"type": "string"}, "kind": {
            "type": "string", "enum": ["human", "agent", "migration"]},
        "label": {"type": "string"},
    }, "required": ["id", "kind", "label"], "additionalProperties": False,
}
COMMON = {
    "expected_head": {"type": "string"},
    "idempotency_key": {"type": "string"},
    "actor": ACTOR,
    "summary": {"type": "string"},
    "occurred_on": {"type": ["string", "null"]},
    "occurred_at": {"type": ["string", "null"]},
}
BASE_REQUIRED = ["expected_head", "idempotency_key", "actor", "summary"]
TOOL_FIELDS = {
    "read": ({"record_id": {"type": "string"}}, ["record_id"]),
    "create": ({
        "path": {"type": "string"}, "content": {"type": "string"},
        "publish_current": {"type": "boolean"},
    }, ["path", "content"]),
    "update": ({
        "record_id": {"type": "string"},
        "expected_version": {"type": "string"},
        "content": {"type": "string"},
        "publish_current": {"type": "boolean"},
    }, ["record_id", "expected_version", "content"]),
    "move": ({
        "record_id": {"type": "string"},
        "expected_version": {"type": "string"},
        "destination": {"type": "string"},
    }, ["record_id", "expected_version", "destination"]),
    "archive": ({
        "record_id": {"type": "string"},
        "expected_version": {"type": "string"},
    }, ["record_id", "expected_version"]),
    "reopen": ({
        "record_id": {"type": "string"},
        "expected_version": {"type": "string"},
        "status": {"type": "string",
                   "enum": ["draft", "stable", "completed"]},
    }, ["record_id", "expected_version", "status"]),
}
DESCRIPTIONS = {
    "read": "Read current canonical record, version and head by ID (trusted local checkout)",
    "create": "Create a record through one native log and CAS transaction",
    "update": "Replace current record with a new append-only version",
    "move": "Atomically move a record and repair authorized relative links",
    "archive": "Mark a record deprecated without deleting history",
    "reopen": "Reopen an archived record with explicit status",
}


def tool_list():
    tools = []
    for command, (specific, required) in TOOL_FIELDS.items():
        properties = ({} if command == "read" else dict(COMMON))
        properties.update(specific)
        tools.append({
            "name": "knowledge_" + command,
            "description": DESCRIPTIONS[command] + "; actor is caller-supplied provenance",
            "inputSchema": {
                "type": "object", "properties": properties,
                "required": required + ([] if command == "read" else BASE_REQUIRED),
                "additionalProperties": False,
            },
        })
    return tools


def _jsonrpc_error(code, message=None, identifier=None):
    return {
        "jsonrpc": "2.0", "id": identifier,
        "error": {"code": code, "message": message or ERRORS.get(code, "Error")},
    }


def _tool_result(result, *, failed=False):
    return {
        "content": [{"type": "text",
                     "text": json.dumps(result, ensure_ascii=False,
                                        separators=(",", ":"))}],
        "isError": failed,
    }


def _dispatch(writer, message):
    """Handle a valid JSON-RPC request, returning only its result or error."""
    method = message["method"]
    params = message.get("params", {})
    if type(params) is not dict:
        raise ValueError("params must be object")
    if method == "initialize":
        protocol = params.get("protocolVersion", "2025-11-25")
        if protocol not in SUPPORTED_PROTOCOLS:
            protocol = "2025-11-25"
        return {
            "protocolVersion": protocol,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "knowledge-hub-local", "version": "1.0.0"},
            "instructions": ("Trusted local Git checkout only. Actor labels "
                             "are caller-supplied provenance, not authenticated."),
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": tool_list()}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if type(name) is not str or not name.startswith("knowledge_") or (
                name[10:] not in TOOL_FIELDS):
            raise ValueError("Unknown tool")
        if type(args) is not dict or "command" in args:
            raise ValueError("Invalid tool arguments")
        command = name[10:]
        properties, required = TOOL_FIELDS[command]
        supported = set(properties) | (set() if command == "read" else set(COMMON))
        required = set(required) | (set() if command == "read" else set(BASE_REQUIRED))
        if set(args) - supported or required - set(args):
            raise ValueError("Invalid tool argument fields")
        request = {**args, "command": command}
        try:
            return _tool_result(execute(writer, request))
        except WriterError as exc:
            return _tool_result(exc.response(), failed=True)
        except Exception:
            return _tool_result(
                WriterError("WRITE_FAILED",
                            "Trusted local operation failed; retry same idempotency key",
                            retryable=True).response(), failed=True)
    raise LookupError("Unknown MCP method")


def answer(writer, raw):
    """One inbound newline-framed message; notifications receive no reply."""
    try:
        value = decode_json(raw, maximum=MAX_MESSAGE)
    except WriterError:
        return _jsonrpc_error(-32700)
    if type(value) is not dict:
        return _jsonrpc_error(-32600)
    identifier = value.get("id")
    has_id = "id" in value
    if (value.get("jsonrpc") != "2.0" or
            not isinstance(value.get("method"), str) or
            (has_id and (type(identifier) not in (str, int)))):
        return _jsonrpc_error(-32600, identifier=identifier if has_id else None)
    if not has_id:
        # notifications/initialized and notifications/cancelled require
        # no response. Never mistakenly commit a mutation as a notification.
        return None
    try:
        result = _dispatch(writer, value)
    except LookupError:
        return _jsonrpc_error(-32601, identifier=identifier)
    except (ValueError, TypeError):
        return _jsonrpc_error(-32602, identifier=identifier)
    except Exception:
        return _jsonrpc_error(-32603, identifier=identifier)
    return {"jsonrpc": "2.0", "id": identifier, "result": result}


def run(writer, source=None, target=None):
    source = source or sys.stdin.buffer
    target = target or sys.stdout.buffer
    while True:
        raw = source.readline(MAX_MESSAGE + 2)
        if not raw:
            return
        if len(raw) > MAX_MESSAGE + 1:
            reply = _jsonrpc_error(-32700, "Request exceeds framing limit")
        else:
            reply = answer(writer, raw)
        if reply is None:
            continue
        payload = json.dumps(reply, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8") + b"\n"
        target.write(payload)
        target.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--capability-file", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--remote", default=None)
    args = parser.parse_args()
    try:
        writer = new_writer(root=args.root, capability_file=args.capability_file,
                            branch=args.branch, remote=args.remote)
    except Exception:
        print("Trusted Knowledge Hub MCP launch configuration unavailable",
              file=sys.stderr)
        return 2
    run(writer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
