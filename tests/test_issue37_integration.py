"""#37 integrated real-Git transport -> policy -> projection -> no-Git smoke.

This test uses the real CLI + stdio MCP (not a pretend agent client),
the actual trusted Git writer, a deliberate private-to-public history
transition, a reviewed synthetic publication allowlist and a pinned bundle.
It covers an integrated backend chain; not 60/60 or #40 agent acceptance.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "records"))
sys.path.insert(0, str(ROOT / "tools" / "projection"))
from test_transport_v1 import TransportGitFixtures, git
from validate_v1 import parse_log
from build import publish
from sourcebundle import create_bundle


class IntegratedNativeFlow(unittest.TestCase):
    def setUp(self):
        self.harness = TransportGitFixtures(
            "test_every_cli_and_real_stdio_tool_share_identical_commit_bytes"
        )
        self.harness.setUp()
        self.addCleanup(self.harness.doCleanups)

    def test_real_transport_public_boundary_and_nogit_generation(self):
        hub = self.harness
        current_path = "openwiki/notes/public-flow.md"
        created = hub.command(
            "create", path=current_path,
            content='---\ntype: note\ntitle: "Integrated stable"\n'
                    'status: stable\nvisibility: public\n---\n\nInitial public content\n',
        )
        returncode, first = hub.cli(created)
        self.assertEqual(returncode, 0)
        self.assertEqual(first["status"], "committed")
        read_error, current = hub.mcp("read", {"record_id": first["record_id"]})
        self.assertFalse(read_error)
        self.assertIn("Initial public content", current["content"])
        self.assertEqual(current["head"], first["head"])
        self.assertEqual(current["version"], first["version"])

        updated = hub.command(
            "update", record_id=first["record_id"], expected_version=first["version"],
            content=current["content"].replace("Initial public content", "Updated public content"),
        )
        update_error, second = hub.mcp("update", updated)
        self.assertFalse(update_error)
        self.assertEqual(second["status"], "committed")
        self.assertEqual(second["record_id"], first["record_id"])

        moved_path = "openwiki/projects/moved-public-flow.md"
        move = hub.command(
            "move", record_id=first["record_id"], expected_version=second["version"],
            destination=moved_path,
        )
        moved_status, moved = hub.cli(move)
        self.assertEqual(moved_status, 0)
        archived = hub.command(
            "archive", record_id=first["record_id"], expected_version=moved["version"]
        )
        archive_error, archived_reply = hub.mcp("archive", archived)
        self.assertFalse(archive_error)
        reopened = hub.command(
            "reopen", record_id=first["record_id"],
            expected_version=archived_reply["version"], status="stable",
        )
        reopen_status, reopened_reply = hub.cli(reopened)
        self.assertEqual(reopen_status, 0)
        self.assertEqual(reopened_reply["publication"], "pending")

        # A separate record's private BEFORE must not enter its public history
        # even when publication policy explicitly allowlists those event IDs.
        secret_path = "openwiki/notes/private-transition.md"
        private_marker = "SYNTHETIC_PRIVATE_BEFORE_ONLY_56e2"
        private_request = hub.command(
            "create", path=secret_path,
            content='---\ntype: note\ntitle: "Transition test"\n'
                    'status: draft\nvisibility: private\n---\n\n' + private_marker + '\n',
        )
        code, secret = hub.cli(private_request)
        self.assertEqual(code, 0)
        error, secret_current = hub.mcp("read", {"record_id": secret["record_id"]})
        self.assertFalse(error)
        published = secret_current["content"].replace('visibility: "private"', 'visibility: "public"')
        published = published.replace(private_marker, "Approved public-after content")
        # Private historical title must not be silently reused as a public
        # current title; the byte-level publication audit rejects that leak.
        published = published.replace("Transition test", "Approved transition record")
        self.assertNotIn(private_marker, published)
        publish_request = hub.command(
            "update", record_id=secret["record_id"],
            expected_version=secret["version"], content=published,
        )
        error, secret_after = hub.mcp("update", publish_request)
        self.assertFalse(error)
        self.assertEqual(secret_after["status"], "committed")

        snapshot = hub.snapshot()
        self.assertNotIn(current_path, snapshot)
        self.assertIn(moved_path, snapshot)
        public_history = parse_log(snapshot[moved_path[:-3] + ".log.md"],
                                   moved_path[:-3] + ".log.md")
        transition_history = parse_log(snapshot[secret_path[:-3] + ".log.md"],
                                       secret_path[:-3] + ".log.md")
        self.assertEqual([event["action"] for event in public_history],
                         ["CREATED", "UPDATED", "MOVED", "ARCHIVED", "REOPENED"])
        self.assertEqual(len(transition_history), 2)
        self.assertEqual(transition_history[0]["after"].find(private_marker) >= 0, True)
        self.assertEqual(transition_history[1]["after"].find(private_marker), -1)
        self.assertEqual(transition_history[-1]["after"], snapshot[secret_path].decode())

        # Public approval is a *separate Git policy commit*, not a write-side
        # mutation. Include the dangerous transition IDs to prove filtering.
        policy = {
            "schema_version": 1,
            "record_ids": sorted([first["record_id"], secret["record_id"]]),
            "event_ids": sorted([event["id"] for event in public_history + transition_history]),
            "actor_labels": ["Caller supplied actor"],
        }
        # GitRecordWriter advances refs without updating the caller worktree.
        # Resynchronize before making a separate policy-only commit; otherwise
        # Git's stale index can erase every native record and history file.
        git(hub.root, "reset", "--hard", "HEAD")
        (hub.root / "config").mkdir(exist_ok=True)
        (hub.root / "config/publication.json").write_text(
            json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        git(hub.root, "add", "config/publication.json")
        git(hub.root, "commit", "-qm", "explicit synthetic approval")
        revision = hub.head()

        with tempfile.TemporaryDirectory() as outputs:
            output = Path(outputs)
            private_manifest = publish(hub.root, output / "private", revision, mode="private")
            public_manifest = publish(hub.root, output / "public", revision, mode="public")
            public_root = output / "public" / "g" / public_manifest["generation"]
            private_root = output / "private" / "g" / private_manifest["generation"]
            public_catalog = json.loads((public_root / "catalog.json").read_text())
            private_catalog = json.loads((private_root / "catalog.json").read_text())
            self.assertEqual((private_catalog["record_count"], private_catalog["event_count"]), (2, 7))
            self.assertEqual((public_catalog["record_count"], public_catalog["event_count"]), (2, 5))
            self.assertEqual(json.loads((public_root / "history" /
                               secret["record_id"] / "index.json").read_text())["event_count"], 0)
            aliases = json.loads((public_root / "aliases.json").read_text())
            self.assertEqual(aliases["paths"][current_path], [first["record_id"]])
            self.assertNotEqual(private_manifest["generation"], public_manifest["generation"])
            for path in list(public_root.rglob("*.json")) + [output / "public" / "manifest.json"]:
                self.assertNotIn(private_marker.encode(), path.read_bytes(), str(path))
                for excluded in transition_history:
                    self.assertNotIn(excluded["id"].encode(), path.read_bytes(), str(path))

            bundle_path = output / "synthetic-source.bundle.json"
            receipt_path = output / "synthetic-receipt.json"
            create_bundle(hub.root, revision, bundle_path, receipt_path)
            expected_pin = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            no_git_manifest = publish(
                None, output / "bundle-public", mode="public", bundle=bundle_path,
                receipt=receipt_path, receipt_sha256=expected_pin,
            )
            self.assertEqual(no_git_manifest["generation"], public_manifest["generation"])
            paired_root = output / "bundle-public" / "g" / no_git_manifest["generation"]
            original = {p.relative_to(public_root).as_posix(): p.read_bytes()
                        for p in public_root.rglob("*.json")}
            rebuilt = {p.relative_to(paired_root).as_posix(): p.read_bytes()
                       for p in paired_root.rglob("*.json")}
            self.assertEqual(original, rebuilt, "No-Git synthetic rebuild differs from public Git output")


if __name__ == "__main__":
    unittest.main()
