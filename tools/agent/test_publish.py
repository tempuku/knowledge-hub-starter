#!/usr/bin/env python3
"""Integration tests for the local Git-backed agent adapter.

Run: python3 -m unittest discover -s tools/agent -p 'test_*.py'
Requires git and PyYAML; uses disposable repositories only.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess

SCRIPT = Path(__file__).with_name("publish.py")
spec = importlib.util.spec_from_file_location("agent_publish", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AgentPublishIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_git("init")
        self.run_git("config", "user.name", "Test Agent")
        self.run_git("config", "user.email", "agent@example.invalid")
        self.record = self.root / "openwiki" / "concepts" / "sample.md"
        self.record.parent.mkdir(parents=True)
        self.record.write_text("---\ntype: concept\ntitle: Sample\nvisibility: public\n---\n\nOld\n")
        self.run_git("add", ".")
        self.run_git("commit", "-m", "initial")
        self.patcher = patch.object(module, "ROOT", self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def run_git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def request(self, key="sample-update"):
        return {"record": "openwiki/concepts/sample.md",
                "expected_head": self.run_git("rev-parse", "HEAD"),
                "content": "---\ntype: concept\ntitle: Sample\nvisibility: public\n---\n\nNew\n",
                "summary": "Changed sample text", "actor": "agent:test", "idempotency_key": key}

    def test_commit_has_source_and_diary(self):
        result = module.publish(self.request())
        self.assertEqual(result["status"], "committed")
        files = self.run_git("show", "--pretty=format:", "--name-only", "HEAD")
        self.assertIn("openwiki/concepts/sample.md", files)
        self.assertIn(result["journal"], files)
        self.assertIn("index.md", files)
        journal = (self.root / result["journal"]).read_text()
        self.assertIn("idempotency_key: sample-update", journal)
        self.assertIn("before:", journal)
        self.assertIn("after: SELF", journal)

    def test_replay_does_not_commit_again(self):
        request = self.request()
        module.publish(request)
        head = self.run_git("rev-parse", "HEAD")
        replay = module.publish(request)
        self.assertEqual(replay["status"], "already_committed")
        self.assertEqual(head, self.run_git("rev-parse", "HEAD"))

    def test_invalid_private_record_rejected(self):
        request = self.request()
        request["content"] = request["content"].replace("visibility: public", "visibility: private")
        with self.assertRaises(ValueError):
            module.publish(request)
        self.assertEqual(self.run_git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
