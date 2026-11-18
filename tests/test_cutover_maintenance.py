"""M-04 maintenance kill-switch regression checks against disposable Git repos."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "records"))
from maintenance_v1 import ENV, writes_paused
from service_v1 import GitRecordWriter
from writer_v1 import WriterError


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def legacy_module(filename):
    path = ROOT / "tools" / "agent" / filename
    name = "cutover_test_" + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Cutover test")
        (self.root / "openwiki").mkdir()
        (self.root / "openwiki" / "index.md").write_text(
            '---\\nokf_version: "0.2"\\n---\\n\\n# Knowledge Hub\\n')
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "initial")
        self.original = git(self.root, "rev-parse", "HEAD")

    def assert_unchanged(self):
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), self.original)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_flag_is_fail_closed_on_unrecognized_values(self):
        for value in ("1", "true", "", "undefined", "off"):
            self.assertTrue(writes_paused({ENV: value}), value)
        self.assertFalse(writes_paused({ENV: "0"}))
        self.assertFalse(writes_paused({}))

    def test_v1_writer_blocks_all_mutations_before_domain_execution(self):
        capability = {"repository_mode": "private", "publisher_scope": False,
                      "operations": ["read", "create", "update", "move",
                                     "archive", "reopen"]}
        writer = GitRecordWriter(self.root, capability)
        for flag in ("1", "typo"):
            with self.subTest(flag=flag), patch.dict(os.environ, {ENV: flag}):
                with self.assertRaises(WriterError) as failure:
                    writer.write({"command": "create"})
                self.assertEqual(failure.exception.code, "MAINTENANCE")
                self.assertTrue(failure.exception.retryable)
                self.assert_unchanged()

        # An explicitly released maintenance flag restores normal validation,
        # not an unguarded write or an automatic replay.
        with patch.dict(os.environ, {ENV: "0"}):
            with self.assertRaises(WriterError) as failure:
                writer.write({"command": "create"})
            self.assertEqual(failure.exception.code, "VALIDATION_ERROR")
        self.assert_unchanged()

    def test_legacy_publishers_are_paused_before_input_is_used(self):
        for filename in ("publish.py", "record_log.py"):
            module = legacy_module(filename)
            with self.subTest(filename=filename):
                with patch.object(module, "ROOT", self.root):
                    with patch.dict(os.environ, {ENV: "1"}):
                        with self.assertRaisesRegex(ValueError, "MAINTENANCE"):
                            module.publish({})
                self.assert_unchanged()


if __name__ == "__main__":
    unittest.main()
