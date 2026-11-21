#!/usr/bin/env python3
"""Local stdio MCP server, eight tools backed by the same v1 Knowledge Hub writer.

Standard MCP stdio framing is one UTF-8 JSON-RPC object per newline, NOT
HTTP Content-Length headers. A server is launched by a trusted local client
with an external authorization profile; no network listener, verified remote
identity or unauthenticated HTTP endpoint exists.

Discovery is read-only: knowledge_search ranks current record metadata and
knowledge_history lists one record's native events. Neither returns private
snapshots in a public repository capability.

Actor metadata inside tool arguments is SUPPLIED provenance, not attested.
"""
from __future__ import annotations

import argparse
import json
import sys

from knowledge_service import (MAX_REQUEST_BYTES, WriterError,
                               decode_json, execute, new_writer)
from pr_publish import (PublicationError, WRITER_VALIDATORS, build_body,
                        enable_auto_merge, ensure_pull_request,
                        merged_publication, prepare_publication_branch,
                        publication_branch)
from pr_publish import run as run_command

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
# Read tools are capability-gated by "read" only; they take no write fields.
READ_TOOLS = {
    "read": ({"record_id": {"type": "string"}}, ["record_id"]),
    "search": ({
        "query": {"type": "string"},
        "limit": {"type": "integer"},
        "include_archived": {"type": "boolean"},
    }, ["query"]),
    "history": ({
        "record_id": {"type": "string"},
        "limit": {"type": "integer"},
        "before_sequence": {"type": "integer"},
    }, ["record_id"]),
}
WRITE_TOOLS = {
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
TOOL_FIELDS = {**READ_TOOLS, **WRITE_TOOLS}
DESCRIPTIONS = {
    "read": "Read current canonical record, version and head by ID (trusted local checkout)",
    "search": "Search current records by tokens and return ranked metadata only",
    "history": "List one record's native history events newest first without snapshots",
    "create": "Create a record through one native log and CAS transaction",
    "update": "Replace current record with a new append-only version",
    "move": "Atomically move a record and repair authorized relative links",
    "archive": "Mark a record deprecated without deleting history",
    "reopen": "Reopen an archived record with explicit status",
}


def tool_list():
    tools = []
    for command, (specific, required) in TOOL_FIELDS.items():
        readable = command in READ_TOOLS
        properties = dict(specific)
        expected = list(required)
        if not readable:
            properties.update(COMMON)
            expected += BASE_REQUIRED
        tools.append({
            "name": "knowledge_" + command,
            "description": DESCRIPTIONS[command] + "; actor is caller-supplied provenance",
            "inputSchema": {
                "type": "object", "properties": properties,
                "required": expected,
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


def _request_path(writer, request):
    """Best available record path for a deterministic branch slug."""
    path = request.get("path")
    if isinstance(path, str):
        return path
    record_id = request.get("record_id")
    if isinstance(record_id, str):
        try:
            return writer.read(record_id).get("path")
        except Exception:
            return None
    return None


def _record_details(writer, result):
    """Read current metadata for the PR body; PR flow never echoes bodies."""
    details = {"path": result.get("record_url", ""),
               "record_id": result.get("record_id", ""),
               "title": "", "status": "", "visibility": ""}
    try:
        current = writer.read(result["record_id"])
    except Exception:
        return details
    details["path"] = current.get("path") or details["path"]
    try:
        from validate_v1 import frontmatter
        meta, _ = frontmatter(current["content"])
    except Exception:
        return details
    for key in ("title", "status", "visibility"):
        if isinstance(meta.get(key), str):
            details[key] = meta[key]
    return details


def _attach_publication(writer, result, request, publication, head, runner):
    record = _record_details(writer, result)
    title = "knowledge: " + (record["title"] or record["path"] or "record")
    body = build_body(record, result, request.get("summary", ""),
                      WRITER_VALIDATORS)
    pull_request = ensure_pull_request(
        publication["root"], publication["base"], head, title[:240], body,
        runner=runner)
    # A pull request is never reported as published: publication remains
    # "pending" until a matching generation is actually visible.
    result["pull_request"] = pull_request
    result["auto_merge"] = False
    if (publication.get("auto_merge") and
            pull_request.get("state") == "open" and
            isinstance(pull_request.get("number"), int)):
        merge = enable_auto_merge(publication["root"],
                                  pull_request["number"], runner=runner)
        result["auto_merge"] = (True if merge.get("state") == "enabled"
                                else merge)
    return result


def _publication_write(writer, request, publication, runner, writer_factory):
    """Create the per-mutation branch, then run the same domain writer."""
    if not isinstance(request.get("idempotency_key"), str):
        raise PublicationError("VALIDATION_ERROR", "Invalid idempotency key")
    head = publication_branch(request["idempotency_key"],
                              _request_path(writer, request))
    prepare_publication_branch(
        publication["root"], publication["remote"], head,
        request.get("expected_head"), runner=runner,
        merged_check=lambda: merged_publication(publication["root"], head,
                                                runner=runner))
    branch_writer = writer_factory(head)
    result = execute(branch_writer, request)
    if (type(result) is dict and result.get("status") in
            ("committed", "already_committed")):
        _attach_publication(branch_writer, result, request, publication,
                            head, runner)
    return result


def _default_writer_factory(publication):
    def factory(branch):
        return new_writer(root=publication["root"],
                          capability_file=publication["capability_file"],
                          branch=branch, remote=publication["remote"])
    return factory


def _dispatch(writer, message, publication=None, *, runner=None,
              writer_factory=None):
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
            "instructions": ("Trusted local Git checkout only. knowledge_search "
                             "and knowledge_history expose ranked metadata and "
                             "event metadata; actor labels are caller-supplied "
                             "provenance, not authenticated."),
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
        supported = set(properties)
        expected = set(required)
        if command not in READ_TOOLS:
            supported |= set(COMMON)
            expected |= set(BASE_REQUIRED)
        if set(args) - supported or expected - set(args):
            raise ValueError("Invalid tool argument fields")
        request = {**args, "command": command}
        try:
            if publication is None or command in READ_TOOLS:
                # Read-only and non-PR launches keep the original behavior;
                # no Git branch, gh command or extra response field is added.
                return _tool_result(execute(writer, request))
            factory = (writer_factory if writer_factory is not None
                       else _default_writer_factory(publication))
            return _tool_result(_publication_write(
                writer, request, publication, runner or run_command, factory))
        except PublicationError as exc:
            return _tool_result(exc.response(), failed=True)
        except WriterError as exc:
            return _tool_result(exc.response(), failed=True)
        except Exception:
            return _tool_result(
                WriterError("WRITE_FAILED",
                            "Trusted local operation failed; retry same idempotency key",
                            retryable=True).response(), failed=True)
    raise LookupError("Unknown MCP method")


def answer(writer, raw, publication=None, *, runner=None, writer_factory=None):
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
        result = _dispatch(writer, value, publication,
                           runner=runner, writer_factory=writer_factory)
    except LookupError:
        return _jsonrpc_error(-32601, identifier=identifier)
    except (ValueError, TypeError):
        return _jsonrpc_error(-32602, identifier=identifier)
    except Exception:
        return _jsonrpc_error(-32603, identifier=identifier)
    return {"jsonrpc": "2.0", "id": identifier, "result": result}


def run(writer, source=None, target=None, publication=None, *, runner=None,
        writer_factory=None):
    source = source or sys.stdin.buffer
    target = target or sys.stdout.buffer
    while True:
        raw = source.readline(MAX_MESSAGE + 2)
        if not raw:
            return
        if len(raw) > MAX_MESSAGE + 1:
            reply = _jsonrpc_error(-32700, "Request exceeds framing limit")
        else:
            reply = answer(writer, raw, publication, runner=runner,
                           writer_factory=writer_factory)
        if reply is None:
            continue
        payload = json.dumps(reply, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8") + b"\n"
        target.write(payload)
        target.flush()


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--capability-file", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--remote", default=None)
    parser.add_argument(
        "--pr-base", default=None,
        help="Enable pull-request publication against this base branch")
    parser.add_argument(
        "--auto-merge", action="store_true",
        help="Enable squash auto-merge for created pull requests "
             "(requires --pr-base)")
    return parser


def main():
    args = build_parser().parse_args()
    if args.auto_merge and not args.pr_base:
        print("--auto-merge requires --pr-base", file=sys.stderr)
        return 2
    publication = None
    if args.pr_base:
        # PR mode writes to a deterministic per-mutation head; --branch stays
        # the startup branch for reads and for non-PR launches.
        remote = args.remote or "origin"
        publication = {"root": args.root, "base": args.pr_base,
                       "remote": remote,
                       "auto_merge": bool(args.auto_merge),
                       "capability_file": args.capability_file}
    try:
        writer = new_writer(root=args.root, capability_file=args.capability_file,
                            branch=args.branch, remote=args.remote)
    except Exception:
        print("Trusted Knowledge Hub MCP launch configuration unavailable",
              file=sys.stderr)
        return 2
    run(writer, publication=publication)
    return 0


if __name__ == "__main__":
    sys.exit(main())
