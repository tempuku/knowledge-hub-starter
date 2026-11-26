"""Strict native-only candidate gate for M-04 source and portable bundles."""
from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from deterministic import ProjectionError
from git_source import load_bundle, load_revision
from sourcebundle import create_bundle
from build import publish


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


class NativeCutoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.name", "Fixture")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        (self.root / "openwiki").mkdir()
        self.put("openwiki/index.md", '# Knowledge Hub\n')
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "initial")

    def put(self, path, value):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(value, encoding="utf-8")

    def commit(self):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "fixture change")
        return git(self.root, "rev-parse", "HEAD")

    def bundle(self):
        folder = self.root / "_out"
        folder.mkdir(exist_ok=True)
        bundle = folder / "bundle.json"
        receipt = folder / "receipt.json"
        create_bundle(self.root, "HEAD", bundle, receipt)
        return bundle, receipt, hashlib.sha256(receipt.read_bytes()).hexdigest()

    def test_legacy_record_is_not_silently_dropped_in_git_or_bundle(self):
        self.put("records/notes/legacy.md",
                 "---\ntype: note\ntitle: Legacy\n---\n\nUnique legacy content\n")
        rev = self.commit()
        # Transitional export is still allowed before an authorized cutover.
        self.assertEqual(load_revision(self.root, rev)[2], [])
        with self.assertRaisesRegex(ProjectionError, "unmigrated record"):
            load_revision(self.root, rev, strict_native=True)
        bundle, receipt, digest = self.bundle()
        with self.assertRaisesRegex(ProjectionError, "unmigrated record"):
            load_bundle(bundle, receipt, digest, strict_native=True)

    def test_dated_journal_refused_even_without_a_record(self):
        self.put("records/journal/2026/11/18/index.md", "# Old dated journal\n")
        rev = self.commit()
        with self.assertRaisesRegex(ProjectionError, "legacy journal"):
            load_revision(self.root, rev, strict_native=True)

    def test_directory_log_refused(self):
        self.put("records/notes/log.md", "# Unique legacy log\n")
        rev = self.commit()
        with self.assertRaisesRegex(ProjectionError, "directory log"):
            load_revision(self.root, rev, strict_native=True)

    def test_old_sibling_log_must_be_archived_before_cutover(self):
        self.put("records/CI.log.md", "# OKF Record Change Log\\n")
        rev = self.commit()
        with self.assertRaisesRegex(ProjectionError, "unmigrated legacy log"):
            load_revision(self.root, rev, strict_native=True)

    def test_root_legacy_guides_explicitly_allowed(self):
        self.put("openwiki/GUIDE.md", "# Legacy guide\n")
        self.put("openwiki/CI.md", "# Legacy CI guide\n")
        rev = self.commit()
        self.assertEqual(load_revision(self.root, rev, strict_native=True)[2], [])
        bundle, receipt, digest = self.bundle()
        self.assertEqual(load_bundle(bundle, receipt, digest, strict_native=True)[2], [])

    def test_strict_build_keeps_previous_live_manifest_on_legacy_source(self):
        self.put("records/notes/legacy.md",
                 "---\ntype: note\ntitle: Unique\n---\n\nThis must not vanish\n")
        rev = self.commit()
        published = self.root / "_public"
        published.mkdir()
        (published / "manifest.json").write_text("previous live generation\n")
        with self.assertRaisesRegex(ProjectionError, "unmigrated record"):
            publish(self.root, published, rev, mode="private", strict_native=True)
        self.assertEqual((published / "manifest.json").read_text(),
                         "previous live generation\n")


if __name__ == "__main__":
    unittest.main()
