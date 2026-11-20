#!/usr/bin/env python3
"""Issue #40/#104: real official MCP SDK client against disposable local Git.

This is NOT a JSON-RPC simulator: ClientSession and stdio_client are supplied
by the upstream modelcontextprotocol Python SDK. No LLM or remote agent is
claimed. The client performs tool discovery and tool calls for the eight-tool
API, including the read-only discovery tools knowledge_search and
knowledge_history; the native committed Git log is still parsed independently
as a cross-check. All data and the capability file are disposable and
synthetic.
"""
from __future__ import annotations

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
    "read", "search", "history", "create", "update", "move", "archive", "reopen"
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

    def set_capability(self, operations: list[str], mode: str = "private") -> None:
        self.capfile.write_text(json.dumps({
            "repository_mode": mode,
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

    def validate_repository(self, expected: dict) -> None:
        with tempfile.TemporaryDirectory(prefix="kh-issue40-validation-") as tmp:
            git(self.root, "worktree", "add", "--detach", tmp, self.head())
            try:
                self.assertEqual(repository(
                    Path(tmp), base=self.initial_head, strict_indexes=True
                ), expected)
            finally:
                git(self.root, "worktree", "remove", "--force", tmp)

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

                # Discovery from prompt text alone: the caller has no UUID yet.
                failed, found = await tool(session, "search",
                                           {"query": "synthetic"})
                self.assertFalse(failed, found)
                self.assertEqual(set(found),
                                 {"query", "head", "total", "count", "results"})
                self.assertEqual(found["query"], "synthetic")
                self.assertEqual(found["head"], updated["head"])
                self.assertEqual(found["total"], 1)
                self.assertEqual(found["count"], 1)
                self.assertEqual(len(found["results"]), 1)
                hit = found["results"][0]
                self.assertEqual(set(hit),
                                 {"record_id", "path", "title", "status"})
                self.assertEqual(hit["record_id"], created["record_id"])
                self.assertEqual(hit["path"], path)
                self.assertEqual(hit["title"], "Synthetic client")
                self.assertEqual(hit["status"], "draft")
                search_text = json.dumps(found)
                # Metadata only: no current/previous body bytes may leak.
                self.assertNotIn("Second version", search_text)
                self.assertNotIn("First version", search_text)
                transcript.append({"step": "search", "total": found["total"],
                                   "count": found["count"], "result": "PASS"})

                failed, discovered = await tool(
                    session, "read", {"record_id": hit["record_id"]}
                )
                self.assertFalse(failed, discovered)
                self.assertEqual(discovered["record_id"], created["record_id"])
                self.assertEqual(discovered["path"], path)
                self.assertEqual(discovered["version"], updated["event_id"])
                self.assertIn("Second version", discovered["content"])
                transcript.append({"step": "read-discovered", "result": "PASS"})

                # History through the SDK: newest first, metadata only.
                failed, events = await tool(session, "history",
                                            {"record_id": created["record_id"]})
                self.assertFalse(failed, events)
                self.assertEqual(set(events), {
                    "record_id", "path", "title", "status", "head", "total",
                    "next", "events",
                })
                self.assertEqual(events["record_id"], created["record_id"])
                self.assertEqual(events["path"], path)
                self.assertEqual(events["title"], "Synthetic client")
                self.assertEqual(events["status"], "draft")
                self.assertEqual(events["head"], updated["head"])
                self.assertEqual(events["total"], 2)
                self.assertIsNone(events["next"])
                self.assertEqual([item["sequence"] for item in events["events"]],
                                 [2, 1])
                self.assertEqual([item["action"] for item in events["events"]],
                                 ["UPDATED", "CREATED"])
                newest = events["events"][0]
                self.assertEqual(newest["event_id"], updated["event_id"])
                self.assertEqual(newest["summary"], update_request["summary"])
                self.assertEqual(newest["actor_label"],
                                 update_request["actor"]["label"])
                self.assertEqual(newest["path_before"], path)
                self.assertEqual(newest["path_after"], path)
                self.assertEqual(newest["record_url"], path)
                self.assertEqual(newest["event_url"],
                                 path[:-3] + ".log.md#" + updated["event_id"])
                for item in events["events"]:
                    self.assertEqual(set(item), {
                        "event_id", "sequence", "action", "recorded_at",
                        "summary", "occurred_on", "occurred_at", "actor_label",
                        "path_before", "path_after", "record_url", "event_url",
                    })
                    for forbidden in ("before", "after", "before_sha256",
                                      "after_sha256", "request_sha256"):
                        self.assertNotIn(forbidden, item)
                history_text = json.dumps(events)
                self.assertNotIn("Second version", history_text)
                self.assertNotIn("First version", history_text)
                transcript.append({"step": "history", "total": events["total"],
                                   "events": [item["action"] for item in
                                              events["events"]],
                                   "result": "PASS"})

                # The cursor pages backwards over the older eligible event.
                failed, older = await tool(session, "history", {
                    "record_id": created["record_id"],
                    "before_sequence": 2, "limit": 1,
                })
                self.assertFalse(failed, older)
                self.assertEqual(older["record_id"], created["record_id"])
                self.assertEqual(older["total"], 2)
                self.assertIsNone(older["next"])
                self.assertEqual([item["sequence"] for item in older["events"]],
                                 [1])
                self.assertEqual([item["action"] for item in older["events"]],
                                 ["CREATED"])
                self.assertEqual(older["events"][0]["event_id"],
                                 created["event_id"])
                self.assertNotIn("First version", json.dumps(older))
                transcript.append({"step": "history-older-page", "total":
                                   older["total"], "result": "PASS"})

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

        # Read the append-only history from real committed Git bytes and check
        # that the MCP history tool reports exactly the same native events.
        log_path = path[:-3] + ".log.md"
        native_log = subprocess.check_output(
            ["git", "show", "main:" + log_path], cwd=self.root
        )
        history = parse_log(native_log, log_path)
        self.assertEqual([entry["action"] for entry in history],
                         ["CREATED", "UPDATED"])
        self.assertEqual([entry["sequence"] for entry in history], [1, 2])
        self.assertEqual(history[-1]["id"], updated["event_id"])
        self.assertEqual([item["event_id"] for item in events["events"]],
                         [entry["id"] for entry in reversed(history)])
        self.assertEqual(after["content"], subprocess.check_output(
            ["git", "show", "main:" + path], cwd=self.root,
            text=True,
        ))
        transcript.append({"step": "read-native-git-history",
                           "actions": ["CREATED", "UPDATED"], "result": "PASS"})

        # A separate SDK client using read-only launch capability may discover
        # tools and use every read tool, but MUST NOT gain write rights from
        # caller tool arguments.
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

                # Discovery is gated by the same "read" operation.
                failed, still_found = await tool(session, "search",
                                                 {"query": "synthetic"})
                self.assertFalse(failed, still_found)
                self.assertEqual(still_found["total"], 1)
                self.assertEqual(still_found["results"][0]["record_id"],
                                 created["record_id"])
                failed, still_history = await tool(
                    session, "history", {"record_id": created["record_id"]}
                )
                self.assertFalse(failed, still_history)
                self.assertEqual(still_history["total"], 2)
                self.assertEqual(still_history["events"][0]["event_id"],
                                 updated["event_id"])
                transcript.append({"step": "read-only-permission",
                                   "error": "PUBLICATION_DENIED",
                                   "discovery": "PASS"})

        # Prove the trusted capability file is absent from source history and
        # the Git transaction still meets native history/index invariants.
        self.assertNotIn("trusted-capabilities.json",
                         git(self.root, "ls-tree", "-r", "--name-only", "main"))
        self.validate_repository({"records": 1, "events": 2})

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

    async def test_public_repository_scope_hides_private_records_and_counts(
            self) -> None:
        """Public capability: search/history never rank, count or reveal
        records whose current visibility is not public. Official SDK only."""
        transcript = []
        public_path = "openwiki/notes/issue104-public-scope.md"
        private_path = "openwiki/notes/issue104-private-scope.md"
        public_content = (
            '---\ntype: note\ntitle: "Atlas publication decision"\n'
            'visibility: public\n---\n\nShared atlas decision, first public version\n'
        )
        private_content = (
            '---\ntype: note\ntitle: "Private atlas draft"\n---\n\n'
            'Shared atlas notes with hushpuppy secret\n'
        )

        async with stdio_client(self.server_parameters()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                failed, public_created = await tool(session, "create", call_fields(
                    self.head(), path=public_path, content=public_content
                ))
                self.assertFalse(failed, public_created)
                self.assertEqual(public_created["status"], "committed")
                failed, private_created = await tool(session, "create", call_fields(
                    self.head(), path=private_path, content=private_content
                ))
                self.assertFalse(failed, private_created)
                self.assertEqual(private_created["status"], "committed")
                transcript.append({"step": "private-fixture",
                                   "records": 2, "result": "committed"})

                failed, public_before = await tool(
                    session, "read", {"record_id": public_created["record_id"]}
                )
                self.assertFalse(failed, public_before)
                self.assertIn('visibility: "public"', public_before["content"])
                failed, public_updated = await tool(session, "update", call_fields(
                    self.head(),
                    record_id=public_created["record_id"],
                    expected_version=public_before["version"],
                    content=public_before["content"].replace(
                        "first public version", "second public version"
                    ),
                ))
                self.assertFalse(failed, public_updated)
                self.assertEqual(public_updated["status"], "committed")
                transcript.append({"step": "public-update", "result": "committed"})

        # Flip the trusted launch file to the publication-scoped read profile.
        self.set_capability(["read"], mode="public")
        async with stdio_client(self.server_parameters()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                self.assertEqual({item.name for item in tools.tools}, TOOLS)

                # A token shared by both records only ranks the public one.
                failed, shared = await tool(session, "search",
                                            {"query": "atlas"})
                self.assertFalse(failed, shared)
                self.assertEqual(shared["head"], public_updated["head"])
                self.assertEqual(shared["total"], 1)
                self.assertEqual(shared["count"], 1)
                self.assertEqual([item["record_id"] for item in
                                  shared["results"]],
                                 [public_created["record_id"]])
                self.assertEqual(shared["results"][0]["path"], public_path)
                self.assertEqual(shared["results"][0]["title"],
                                 "Atlas publication decision")
                shared_text = json.dumps(shared)
                self.assertNotIn("hushpuppy", shared_text)
                self.assertNotIn("issue104-private-scope", shared_text)
                self.assertNotIn("second public version", shared_text)
                transcript.append({"step": "public-scope-search",
                                   "total": shared["total"], "result": "PASS"})

                # A private-only token must not even register a count.
                failed, private_only = await tool(session, "search",
                                                  {"query": "hushpuppy"})
                self.assertFalse(failed, private_only)
                self.assertEqual(private_only["total"], 0)
                self.assertEqual(private_only["count"], 0)
                self.assertEqual(private_only["results"], [])
                failed, mixed = await tool(session, "search",
                                           {"query": "atlas hushpuppy"})
                self.assertFalse(failed, mixed)
                self.assertEqual(mixed["total"], 0)
                transcript.append({"step": "public-scope-private-token",
                                   "total": 0, "result": "PASS"})

                # The private record has no visible existence at all.
                failed, hidden_read = await tool(
                    session, "read", {"record_id": private_created["record_id"]}
                )
                self.assertTrue(failed, hidden_read)
                self.assertEqual(hidden_read["code"], "NOT_FOUND")
                failed, hidden_history = await tool(
                    session, "history", {"record_id": private_created["record_id"]}
                )
                self.assertTrue(failed, hidden_history)
                self.assertEqual(hidden_history["code"], "NOT_FOUND")
                transcript.append({"step": "public-scope-hidden-history",
                                   "error": "NOT_FOUND"})

                # The public record's history is still readable and metadata
                # only; the private record's token never appears.
                failed, public_history = await tool(
                    session, "history", {"record_id": public_created["record_id"]}
                )
                self.assertFalse(failed, public_history)
                self.assertEqual(public_history["path"], public_path)
                self.assertEqual(public_history["title"],
                                 "Atlas publication decision")
                self.assertEqual(public_history["status"], "draft")
                self.assertEqual(public_history["head"], public_updated["head"])
                self.assertEqual(public_history["total"], 2)
                self.assertIsNone(public_history["next"])
                self.assertEqual([item["sequence"] for item in
                                  public_history["events"]], [2, 1])
                self.assertEqual([item["action"] for item in
                                  public_history["events"]],
                                 ["UPDATED", "CREATED"])
                self.assertEqual(public_history["events"][0]["event_id"],
                                 public_updated["event_id"])
                public_history_text = json.dumps(public_history)
                self.assertNotIn("hushpuppy", public_history_text)
                self.assertNotIn("issue104-private-scope", public_history_text)
                self.assertNotIn("second public version", public_history_text)
                for item in public_history["events"]:
                    for forbidden in ("before", "after", "before_sha256",
                                      "after_sha256", "request_sha256"):
                        self.assertNotIn(forbidden, item)
                transcript.append({"step": "public-scope-history",
                                   "total": public_history["total"],
                                   "result": "PASS"})

        self.assertNotIn("trusted-capabilities.json",
                         git(self.root, "ls-tree", "-r", "--name-only", "main"))
        self.validate_repository({"records": 2, "events": 3})
        transcript.append({"step": "native-integrity", "result": "PASS"})
        print("Issue #104 sanitized public-scope transcript: " +
              json.dumps(transcript, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
