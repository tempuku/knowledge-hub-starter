#!/usr/bin/env python3
"""Issue #40: real official MCP SDK client against disposable local Git.

This is NOT a JSON-RPC simulator: ClientSession and stdio_client are supplied
by the upstream modelcontextprotocol Python SDK. No LLM or remote agent is
claimed. The client performs tool discovery and tool calls; native history is
verified from the committed Git log because the six-tool API has no history
endpoint. All data and the capability file are disposable and synthetic.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "tools" / "agent" / "mcp_server.py"
sys.path.insert(0, str(REPO / "tools" / "records"))
from validate_v1 import parse_log, repository  # noqa: E402

TOOLS = {"knowledge_" + name for name in (
    "read", "create", "update", "move", "archive", "reopen"
)}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL
    ).strip()


def call_fields(head: str, **fields: object) -> dict:
    return {
        "expected_head": head,
        "idempotency_key": str(uuid.uuid4()),
        "actor": {"id": "synthetic-client", "kind": "agent",
                  "label": "Synthetic MCP SDK client (unverified provenance)"},
        "summary": "Disposable issue 40 SDK smoke",
        **fields,
    }


async def tool(session: ClientSession, name: str, fields: dict) -> tuple[bool, dict]:
    response = await session.call_tool("knowledge_" + name, fields)
    assert len(response.content) == 1 and response.content[0].type == "text"
    payload = json.loads(response.content[0].text)
    assert isinstance(payload, dict)
    return bool(response.isError), payload


class RealSdkClientSmoke(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kh-issue40-")
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.root = base / "disposable-git"
        self.root.mkdir()
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.name", "Synthetic Client")
        git(self.root, "config", "user.email", "client@example.invalid")
        (self.root / "openwiki").mkdir()
        (self.root / "openwiki" / "index.md").write_text(
            '---\nokf_version: "0.2"\n---\n\n# Disposable\n\n', encoding="utf-8"
        )
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "synthetic initial")
        self.initial_head = self.head()
        # The authorization profile is deliberately OUTSIDE the Git checkout.
        self.capfile = base / "trusted-capabilities.json"
        self.set_capability(["read", "create", "update", "move", "archive", "reopen"])

    def set_capability(self, operations: list[str]) -> None:
        self.capfile.write_text(json.dumps({
            "repository_mode": "private",
            "operations": operations,
            "publisher_scope": False,
        }), encoding="utf-8")

    def head(self) -> str:
        return git(self.root, "rev-parse", "refs/heads/main")

    def server_parameters(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER), "--root", str(self.root),
                  "--capability-file", str(self.capfile)],
            cwd=str(REPO),
        )

    async def test_real_client_discovery_round_trip_and_security(self) -> None:
        transcript = []
        path = "openwiki/notes/issue40-synthetic.md"
        content = '---\ntype: note\ntitle: "Synthetic client"\n---\n\nFirst version\n'

        # This is a real SDK session and handshake, not hand-written frames.
        async with stdio_client(self.server_parameters()) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                self.assertEqual(initialized.serverInfo.name, "knowledge-hub-local")
                tools = await session.list_tools()
                self.assertEqual({item.name for item in tools.tools}, TOOLS)
                transcript.append({"step": "sdk-discovery", "tools": sorted(TOOLS),
                                   "result": "PASS"})
                create_request = call_fields(self.head(), path=path, content=content)
                failed, created = await tool(session, "create", create_request)
                self.assertFalse(failed, created)
                self.assertEqual(created["status"], "committed")
                self.assertEqual(created["publication"], "pending")
                transcript.append({"step": "create-seed", "result": "committed"})

                failed, before = await tool(session, "read",
                                            {"record_id": created["record_id"]})
                self.assertFalse(failed, before)
                self.assertEqual(before["version"], created["event_id"])
                self.assertIn("First version", before["content"])
                transcript.append({"step": "read", "result": "PASS"})

                update_request = call_fields(
                    self.head(), record_id=created["record_id"],
                    expected_version=before["version"],
                    content=before["content"].replace(
                        "First version", "Second version"
                    ),
                )
                failed, updated = await tool(session, "update", update_request)
                self.assertFalse(failed, updated)
                self.assertEqual(updated["status"], "committed")
                transcript.append({"step": "write-update", "result": "committed"})

                failed, after = await tool(session, "read",
                                           {"record_id": created["record_id"]})
                self.assertFalse(failed, after)
                self.assertEqual(after["version"], updated["event_id"])
                self.assertEqual(after["head"], self.head())
                self.assertIn("Second version", after["content"])

                # Same operation/key must replay receipt without new commit.
                failed, retried = await tool(session, "update", update_request)
                self.assertFalse(failed, retried)
                self.assertEqual(retried["status"], "already_committed")
                for key in ("event_id", "version", "head", "operation_id"):
                    self.assertEqual(retried[key], updated[key])
                self.assertEqual(self.head(), updated["head"])
                transcript.append({"step": "idempotent-retry",
                                   "result": "already_committed"})

                stale_request = call_fields(
                    self.head(), record_id=created["record_id"],
                    expected_version=created["version"],
                    content=after["content"].replace(
                        "Second version", "Forbidden stale version"
                    ),
                )
                failed, conflict = await tool(session, "update", stale_request)
                self.assertTrue(failed, conflict)
                self.assertEqual(conflict["code"], "CONFLICT")
                self.assertEqual(self.head(), updated["head"])
                transcript.append({"step": "stale-version", "error": "CONFLICT"})

        # Read the append-only history from real committed Git bytes.
        # The existing MCP API exposes current record reads but no history tool.
        log_path = path[:-3] + ".log.md"
        native_log = subprocess.check_output(
            ["git", "show", "main:" + log_path], cwd=self.root
        )
        history = parse_log(native_log, log_path)
        self.assertEqual([entry["action"] for entry in history],
                         ["CREATED", "UPDATED"])
        self.assertEqual([entry["sequence"] for entry in history], [1, 2])
        self.assertEqual(history[-1]["id"], updated["event_id"])
        self.assertEqual(after["content"], subprocess.check_output(
            ["git", "show", "main:" + path], cwd=self.root,
            text=True,
        ))
        transcript.append({"step": "read-native-git-history",
                           "actions": ["CREATED", "UPDATED"], "result": "PASS"})

        # A separate SDK client using read-only launch capability may discover
        # tools, but MUST NOT gain write rights from caller tool arguments.
        self.set_capability(["read"])
        async with stdio_client(self.server_parameters()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                failed, denied = await tool(session, "update", call_fields(
                    self.head(), record_id=created["record_id"],
                    expected_version=updated["version"],
                    content=after["content"].replace(
                        "Second version", "Not authorized"
                    ),
                ))
                self.assertTrue(failed, denied)
                self.assertEqual(denied["code"], "PUBLICATION_DENIED")
                self.assertEqual(self.head(), updated["head"])
                failed, still_readable = await tool(
                    session, "read", {"record_id": created["record_id"]}
                )
                self.assertFalse(failed, still_readable)
                self.assertEqual(still_readable["version"], updated["version"])
                transcript.append({"step": "read-only-permission",
                                   "error": "PUBLICATION_DENIED"})

        # Prove the trusted capability file is absent from source history and
        # the Git transaction still meets native history/index invariants.
        self.assertNotIn("trusted-capabilities.json",
                         git(self.root, "ls-tree", "-r", "--name-only", "main"))
        with tempfile.TemporaryDirectory(prefix="kh-issue40-validation-") as tmp:
            git(self.root, "worktree", "add", "--detach", tmp, self.head())
            try:
                self.assertEqual(repository(
                    Path(tmp), base=self.initial_head, strict_indexes=True
                ), {"records": 1, "events": 2})
            finally:
                git(self.root, "worktree", "remove", "--force", tmp)

        transcript.append({"step": "native-integrity", "result": "PASS"})
        path_to_report = os.environ.get("KH_ISSUE40_REPORT")
        if path_to_report:
            # Transcript intentionally excludes content, client paths,
            # capability files, tokens, actor IDs and any private snapshots.
            Path(path_to_report).write_text(
                json.dumps({"test": "issue40-official-mcp-sdk-client",
                            "client": "mcp==1.30.0", "server": "stdio",
                            "data": "synthetic disposable Git",
                            "head": self.head(), "steps": transcript},
                           indent=2) + "\n", encoding="utf-8"
            )
        print("Issue #40 sanitized SDK-client transcript: " +
              json.dumps(transcript, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
