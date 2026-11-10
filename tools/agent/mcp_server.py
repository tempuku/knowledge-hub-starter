#!/usr/bin/env python3
"""Minimal local stdio MCP adapter (JSON-RPC 2.0, Content-Length framing).

TRUST BOUNDARY: no authentication. Launch only for a trusted local agent.
Do not expose this process on a network or to untrusted clients.
"""
import json
import sys
from pathlib import Path

from publish import ROOT, git, publish

TOOLS = [
    {"name": "knowledge_read", "description": "Read an OKF record and Git HEAD",
     "inputSchema": {"type": "object", "properties": {"record": {"type": "string"}},
                     "required": ["record"]}},
    {"name": "knowledge_publish", "description": "Commit a public OKF update with diary",
     "inputSchema": {"type": "object", "properties": {
         "record": {"type": "string"}, "expected_head": {"type": "string"},
         "content": {"type": "string"}, "summary": {"type": "string"},
         "actor": {"type": "string"}, "idempotency_key": {"type": "string"}},
         "required": ["record", "expected_head", "content", "summary", "actor", "idempotency_key"]}}
]


def read_record(name):
    path = (ROOT / name).resolve()
    if not path.is_relative_to((ROOT / "openwiki").resolve()) or not path.is_file() or path.is_symlink():
        raise ValueError("Invalid OKF record path")
    return {"record": name, "head": git("rev-parse", "HEAD"), "content": path.read_text(encoding="utf-8")}


def dispatch(msg):
    method = msg.get("method")
    args = msg.get("params", {})
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                "serverInfo": {"name": "knowledge-hub-local", "version": "0.1.0"}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name = args.get("name")
        values = args.get("arguments", {})
        try:
            if name == "knowledge_read":
                result = read_record(values["record"])
            elif name == "knowledge_publish":
                result = publish(values)
            else:
                raise ValueError("Unknown tool")
            return {"content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as exc:
            return {"isError": True, "content": [{"type": "text", "text": str(exc)}]}
    raise ValueError("Unknown method")


def run():
    source = sys.stdin.buffer
    target = sys.stdout.buffer
    while True:
        headers = {}
        line = source.readline()
        if not line:
            break
        while line not in (b"\r\n", b"\n", b""):
            key, _, value = line.decode("ascii").partition(":")
            headers[key.lower()] = value.strip()
            line = source.readline()
        size = int(headers["content-length"])
        if size <= 0 or size > 10_000_000:
            raise ValueError("Invalid message size")
        msg = json.loads(source.read(size))
        if "id" not in msg:
            continue
        try:
            response = {"jsonrpc": "2.0", "id": msg["id"], "result": dispatch(msg)}
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": msg["id"],
                        "error": {"code": -32603, "message": str(exc)}}
        raw = json.dumps(response).encode("utf-8")
        target.write(b"Content-Length: " + str(len(raw)).encode("ascii") + b"\r\n\r\n" + raw)
        target.flush()


if __name__ == "__main__":
    run()
