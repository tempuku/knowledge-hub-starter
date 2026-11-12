"""Actual subprocess-level CLI and stdio MCP v1 integration in disposable Git.

No mocked transports or repository writes. Both adapters call one native
GitRecordWriter; commands and idempotent retries must preserve identical
canonical record, history and structural index bytes.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_v1 import parse_log, repository

REPO_SOURCE = Path(__file__).resolve().parents[2]
AGENT = REPO_SOURCE / "tools" / "agent"
CLI = AGENT / "knowledge_cli.py"
MCP = AGENT / "mcp_server.py"
COMMANDS = ("read", "create", "update", "move", "archive", "reopen")


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


class TransportGitFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "private-clone"
        self.root.mkdir()
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.name", "Fixture")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        (self.root / "openwiki").mkdir()
        (self.root / "openwiki/index.md").write_text(
            '---\nokf_version: "0.2"\n---\n\n# Knowledge Hub\n\n', encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "fixture")
        self.initial_head = git(self.root, "rev-parse", "main")
        self.capability_file = base / "trusted-capability.json"
        self.capability = {
            "repository_mode": "private",
            "operations": list(COMMANDS),
            "publisher_scope": False,
        }
        self.set_capability(self.capability)

    def set_capability(self, value):
        self.capability_file.write_text(json.dumps(value), encoding="utf-8")

    def head(self):
        return git(self.root, "rev-parse", "refs/heads/main")

    def command(self, name, **fields):
        return {
            "command": name,
            "actor": {"id": "local-transport", "kind": "agent",
                      "label": "Caller supplied actor"},
            "summary": "Local fixture " + name,
            "idempotency_key": str(uuid.uuid4()),
            "expected_head": self.head(),
            **fields,
        }

    def cli(self, request):
        proc = subprocess.run([
            sys.executable, str(CLI), "--root", str(self.root),
            "--capability-file", str(self.capability_file), "--request", "-",
        ], input=json.dumps(request, ensure_ascii=False) + "\n",
           capture_output=True, text=True, timeout=60)
        self.assertIn(proc.returncode, (0, 2), proc.stderr)
        self.assertEqual(len(proc.stdout.splitlines()), 1, proc.stdout)
        result = json.loads(proc.stdout)
        return proc.returncode, result

    def raw_mcp(self, lines):
        proc = subprocess.run([
            sys.executable, str(MCP), "--root", str(self.root),
            "--capability-file", str(self.capability_file),
        ], input="".join(lines), capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        replies = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(proc.stdout.splitlines()), len(replies))
        return replies, proc.stderr

    def mcp(self, name, request):
        args = {k: v for k, v in request.items() if k != "command"}
        lines = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2025-11-25"}}) + "\n",
            json.dumps({"jsonrpc": "2.0",
                        "method": "notifications/initialized"}) + "\n",
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n",
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "knowledge_" + name,
                                   "arguments": args}},
                       ensure_ascii=False) + "\n",
        ]
        replies, stderr = self.raw_mcp(lines)
        self.assertEqual([r["id"] for r in replies], [1, 2, 3], stderr)
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual({tool["name"] for tool in replies[1]["result"]["tools"]},
                         {"knowledge_" + cmd for cmd in COMMANDS})
        self.assertIn("caller-supplied provenance",
                      replies[1]["result"]["tools"][0]["description"])
        result = replies[2]["result"]
        self.assertEqual(len(result["content"]), 1)
        self.assertEqual(result["content"][0]["type"], "text")
        return result["isError"], json.loads(result["content"][0]["text"])

    def snapshot(self):
        paths = git(self.root, "ls-tree", "-r", "--name-only",
                    "refs/heads/main", "--", "openwiki").splitlines()
        return {
            path: subprocess.check_output(["git", "show", "main:" + path],
                                          cwd=self.root)
            for path in paths
        }

    def assert_retry_is_byte_identical(self, before, retry, initial):
        self.assertFalse(retry[0])
        response = retry[1]
        self.assertEqual(response["status"], "already_committed")
        for name in ("record_id", "event_id", "operation_id", "version", "head",
                     "record_url", "event_url", "diff_url"):
            self.assertEqual(response[name], initial[name], name)
        self.assertEqual(response["publication"], "pending")
        self.assertEqual(self.snapshot(), before)

    def test_every_cli_and_real_stdio_tool_share_identical_commit_bytes(self):
        path = "openwiki/notes/fixture.md"
        create = self.command("create", path=path,
                              content='---\ntype: note\ntitle: "Fixture"\n---\n\n'
                                      '# Part\n\nFirst\n')
        status, first = self.cli(create)
        self.assertEqual(status, 0)
        self.assertEqual(first["status"], "committed")
        self.assertEqual(first["publication"], "pending")
        self.assert_retry_is_byte_identical(
            self.snapshot(), self.mcp("create", create), first)

        read_cli = self.cli({"command": "read", "record_id": first["record_id"]})
        read_mcp = self.mcp("read",
                            {"command": "read", "record_id": first["record_id"]})
        self.assertEqual(read_cli[0], 0)
        self.assertFalse(read_mcp[0])
        self.assertEqual(read_cli[1], read_mcp[1])
        self.assertEqual(read_cli[1]["version"], first["event_id"])
        self.assertEqual(read_cli[1]["head"], first["head"])
        self.assertEqual(read_cli[1]["path"], path)

        update = self.command(
            "update", record_id=first["record_id"],
            expected_version=first["version"],
            content=read_cli[1]["content"].replace("First\n", "Second\n"))
        error, second = self.mcp("update", update)
        self.assertFalse(error)
        self.assertEqual(second["status"], "committed")
        self.assert_retry_is_byte_identical(
            self.snapshot(), (lambda out: (out[0] != 0, out[1]))(self.cli(update)),
            second)

        move = self.command(
            "move", record_id=first["record_id"],
            expected_version=second["version"],
            destination="openwiki/projects/renamed.md")
        status, third = self.cli(move)
        self.assertEqual(status, 0)
        self.assertEqual(third["record_id"], first["record_id"])
        self.assertEqual(third["record_url"], "openwiki/projects/renamed.md")
        self.assertNotIn(path, self.snapshot())
        self.assert_retry_is_byte_identical(
            self.snapshot(), self.mcp("move", move), third)

        archive = self.command(
            "archive", record_id=first["record_id"],
            expected_version=third["version"])
        error, fourth = self.mcp("archive", archive)
        self.assertFalse(error)
        self.assert_retry_is_byte_identical(
            self.snapshot(), (lambda out: (out[0] != 0, out[1]))(self.cli(archive)),
            fourth)
        self.assertIn(b'status: "deprecated"', self.snapshot()["openwiki/projects/renamed.md"])

        reopen = self.command(
            "reopen", record_id=first["record_id"],
            expected_version=fourth["version"], status="stable")
        status, fifth = self.cli(reopen)
        self.assertEqual(status, 0)
        self.assert_retry_is_byte_identical(
            self.snapshot(), self.mcp("reopen", reopen), fifth)
        self.assertEqual(self.head(), fifth["head"])
        log = parse_log(self.snapshot()["openwiki/projects/renamed.log.md"],
                        "openwiki/projects/renamed.log.md")
        self.assertEqual([x["action"] for x in log],
                         ["CREATED", "UPDATED", "MOVED", "ARCHIVED", "REOPENED"])
        self.assertEqual([x["sequence"] for x in log], [1, 2, 3, 4, 5])
        self.assertTrue(all(x["actor"]["label"] == "Caller supplied actor" for x in log))
        with tempfile.TemporaryDirectory() as worktree:
            git(self.root, "worktree", "add", "--detach", worktree, self.head())
            try:
                validated = repository(Path(worktree), base=self.initial_head,
                                       strict_indexes=True)
                self.assertEqual(validated, {"records": 1, "events": 5})
            finally:
                git(self.root, "worktree", "remove", "--force", worktree)

    def test_both_transports_reject_conflicts_idempotency_and_privacy(self):
        path = "openwiki/notes/secret.md"
        request = self.command("create", path=path,
                               content='---\ntype: note\ntitle: "Secret"\n---\n\nText\n')
        self.set_capability({**self.capability, "repository_mode": "public",
                             "publisher_scope": True})
        code, denied = self.cli(request)
        self.assertEqual(code, 2)
        self.assertEqual(denied["code"], "PUBLICATION_DENIED")
        error, mcp_denied = self.mcp("create", request)
        self.assertTrue(error)
        self.assertEqual(mcp_denied["code"], denied["code"])
        self.assertNotIn("Text", json.dumps(mcp_denied))
        self.assertEqual(self.head(), self.initial_head)

        self.set_capability(self.capability)
        status, committed = self.cli(request)
        self.assertEqual(status, 0)
        base = self.head()
        stale = {**request, "idempotency_key": str(uuid.uuid4())}
        code, old_head = self.cli(stale)
        self.assertEqual(code, 2)
        self.assertEqual(old_head["code"], "CONFLICT")
        error, old_mcp = self.mcp("create", stale)
        self.assertTrue(error)
        self.assertEqual(old_mcp["code"], "CONFLICT")
        mutated = {**request, "summary": "Different actor summary"}
        code, collision = self.cli(mutated)
        self.assertEqual(code, 2)
        self.assertEqual(collision["code"], "IDEMPOTENCY_CONFLICT")
        error, same_mcp = self.mcp("create", mutated)
        self.assertTrue(error)
        self.assertEqual(same_mcp["code"], "IDEMPOTENCY_CONFLICT")
        wrong_version = self.command(
            "update", record_id=committed["record_id"],
            expected_version=str(uuid.uuid4()),
            content='---\nid: "' + committed["record_id"] +
                    '"\nschema_version: 1\ntype: note\ntitle: "Secret"\n'
                    'status: draft\nvisibility: private\n---\n\nEdited\n')
        code, ver = self.cli(wrong_version)
        self.assertEqual(code, 2)
        self.assertEqual(ver["code"], "CONFLICT")
        error, ver_mcp = self.mcp("update", wrong_version)
        self.assertTrue(error)
        self.assertEqual(ver_mcp["code"], "CONFLICT")
        self.assertEqual(self.head(), base)

    def test_stdio_framing_protocol_errors_and_capability_injection(self):
        frames = [
            '{"jsonrpc":\n',
            json.dumps({"jsonrpc": "2.0", "id": "init", "method": "initialize",
                        "params": {"protocolVersion": "2026-07-28"}}) + "\n",
            json.dumps({"jsonrpc": "2.0",
                        "method": "notifications/initialized"}) + "\n",
            json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                        "params": {"name": "knowledge_read",
                                   "arguments": {"record_id": "x",
                                                 "capability": {"repository_mode": "private"}}}}) + "\n",
            json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/unknown"}) + "\n",
            json.dumps({"jsonrpc": "2.0", "id": 6, "method": "tools/list"}) + "\n",
        ]
        replies, stderr = self.raw_mcp(frames)
        self.assertEqual(len(replies), 5, stderr)
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(replies[1]["result"]["protocolVersion"], "2026-07-28")
        self.assertEqual(replies[2]["error"]["code"], -32602)
        self.assertEqual(replies[3]["error"]["code"], -32601)
        self.assertEqual(len(replies[4]["result"]["tools"]), 6)
        self.assertEqual(self.head(), self.initial_head)


if __name__ == "__main__":
    unittest.main()
