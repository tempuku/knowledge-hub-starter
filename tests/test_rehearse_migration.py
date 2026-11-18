"""Disposable Git-backed #36 acceptance: P10/P11/P12/P13/P2 and privacy.

Uses only the reviewed frozen public source, never the live repository branch.
All candidate files, archives, bundles and private JSON stay in TemporaryDirectory
and MUST NOT be uploaded as public CI artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rehearse_migration import convert, RehearsalError
from validate_inventory import validate as validate_inventory

BASE = "de749bed9053dd4bc9f96fee3cb7f816e5bdebcb"
TIME = "2026-11-18T12:00:00Z"


def command(cwd, *args):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode:
        # Builders print structural errors only; never raw candidate snapshots.
        raise AssertionError("disposable command failed: " + result.stderr[-1200:])
    return result.stdout.strip()


def file_hashes(root):
    return {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in root.rglob("*") if f.is_file() and ".git" not in f.parts}


class RehearsalAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.space = tempfile.TemporaryDirectory(prefix="kh-36-disposable-")
        cls.temp = Path(cls.space.name)
        cls.source = cls.temp / "frozen"
        command(ROOT, "git", "clone", "--quiet", "--no-hardlinks",
                "--no-checkout", str(ROOT), str(cls.source))
        command(cls.source, "git", "checkout", "--detach", "--quiet", BASE)
        cls.manifest_path = ROOT / "migration/records-v1.json"
        cls.manifest = json.loads(cls.manifest_path.read_text())
        cls.before_source = file_hashes(cls.source)
        cls.first = cls.temp / "candidate-a"
        cls.second = cls.temp / "candidate-b"
        cls.report_a = convert(cls.source, cls.manifest_path, cls.first, BASE, TIME)
        cls.report_b = convert(cls.source, cls.manifest_path, cls.second, BASE, TIME)

    @classmethod
    def tearDownClass(cls):
        cls.space.cleanup()

    def test_p11_same_frozen_source_same_tree_and_bytes(self):
        self.assertEqual(self.report_a["candidate_tree"], self.report_b["candidate_tree"])
        self.assertEqual(self.report_a["candidate_commit"], self.report_b["candidate_commit"])
        self.assertEqual(file_hashes(self.first), file_hashes(self.second))
        self.assertEqual(self.before_source, file_hashes(self.source))
        self.assertEqual(self.report_a["source_count"], 45)
        self.assertEqual(self.report_a["record_count"], 23)
        self.assertEqual(self.report_a["legacy_event_count"], 52)
        self.assertEqual(self.report_a["backfill_count"], 2)
        self.assertEqual(self.report_a["normalization_count"], 23)
        self.assertEqual(self.report_a["migrated_event_count"], 78)

    def test_p10_unique_source_and_alias_mappings(self):
        aliases = json.loads((self.first / "migration/aliases-v1.json").read_text())
        self.assertEqual(len(aliases["paths"]), 23)
        self.assertEqual(len(aliases["entries"]) + len(aliases["current_entries"]), 61)
        self.assertEqual(len(set(aliases["entries"]) & set(aliases["current_entries"])), 0)
        for item in self.manifest["items"]:
            archive = self.first / "migration/legacy" / item["old_path"]
            self.assertTrue(archive.is_file())
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),
                             item["source_sha256"])
            if item["disposition"] != "structural":
                dest = self.first / item["destination_path"]
                self.assertTrue(dest.is_file())
                self.assertTrue((self.first / (item["destination_path"][:-3] + ".log.md")).is_file())
        # A distinct dated note is retained, not deduplicated by title.
        independent = "openwiki/notes/knowledge-hub/diary-diff-demo.md"
        self.assertTrue((self.first / independent).is_file())
        # Reviewed diary demo has two original events, one Git gap repair, and
        # one explicitly visible normalization event; no second bare log row.
        log = self.first / "openwiki/concepts/diary-diff-demo.log.md"
        self.assertEqual(log.read_text().count("## Entry "), 4)

    def test_p13_real_provenance_and_no_invented_occurrence(self):
        paths = ["openwiki/CI.log.md",
                 "openwiki/concepts/diary-diff-demo.log.md",
                 "openwiki/notes/knowledge-hub/november-2026-journal-summary.log.md"]
        logs = []
        for path in paths:
            # CI and the demo remain at their original reviewed destinations.
            text = (self.first / path).read_text()
            logs.append([json.loads(chunk.split("\n\x60\x60\x60json\n")[1].split("\n\x60\x60\x60")[0])
                         for chunk in text.split("## Entry ")[1:] ])
        ci, demo, summary = logs
        self.assertEqual([e["provenance"]["kind"] for e in ci],
                         ["legacy-log", "legacy-log", "git-backfill", "git-backfill", "legacy-log"])
        self.assertEqual([e["sequence"] for e in ci], list(range(1, 6)))
        self.assertEqual(demo[0]["recorded_at"], "2026-11-10T17:38:34Z")
        self.assertEqual(demo[2]["provenance"]["kind"], "git-backfill")
        self.assertEqual(summary[0]["provenance"]["original_time"], None)
        for events in logs:
            for event in events:
                self.assertIsNone(event["occurred_on"])
                self.assertIsNone(event["occurred_at"])
                self.assertTrue(event["provenance"]["source_ref"])

    def test_p12_changed_source_head_rejected_before_output(self):
        path = self.temp / "reject-head"
        with self.assertRaisesRegex(RehearsalError, "EXPECTED_HEAD_MISMATCH"):
            convert(self.source, self.manifest_path, path, "0" * 40, TIME)
        self.assertFalse(path.exists())

    def test_p12_invalid_manifest_bytes_fail_closed(self):
        broken = json.loads(self.manifest_path.read_text())
        broken["items"][0]["source_sha256"] = "0" * 64
        manifest = self.temp / "corrupt.json"
        manifest.write_text(json.dumps(broken))
        output = self.temp / "reject-corrupt"
        with self.assertRaisesRegex(RehearsalError, "reviewed manifest validation failed"):
            convert(self.source, manifest, output, BASE, TIME)
        self.assertFalse(output.exists())

    def test_p2_public_private_and_no_git_bundle_rebuild(self):
        source_bundle = ROOT / "tools/projection/sourcebundle.py"
        builder = ROOT / "tools/projection/build.py"
        generated = self.temp / "private-built"
        public = self.temp / "public-built"
        bundle_path = self.temp / "frozen-candidate.bundle.json"
        receipt_path = self.temp / "frozen-candidate.receipt.json"
        command(ROOT, sys.executable, str(builder), "--root", str(self.first),
                "--revision", "HEAD", "--mode", "private",
                "--destination", str(generated), "--published-at", TIME)
        command(ROOT, sys.executable, str(builder), "--root", str(self.first),
                "--revision", "HEAD", "--mode", "public",
                "--destination", str(public), "--published-at", TIME)
        command(ROOT, sys.executable, str(source_bundle), "--root", str(self.first),
                "--revision", "HEAD", "--output", str(bundle_path),
                "--receipt-output", str(receipt_path))
        receipt_pin = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        shutil.rmtree(self.second / ".git")
        no_git = self.temp / "no-git-built"
        command(ROOT, sys.executable, str(builder),
                "--bundle", str(bundle_path), "--receipt", str(receipt_path),
                "--receipt-sha256", receipt_pin, "--mode", "private",
                "--destination", str(no_git), "--published-at", TIME)
        self.assertEqual(file_hashes(generated), file_hashes(no_git))
        private_catalog = json.loads(next((generated / "g").rglob("catalog.json")).read_text())
        public_catalog = json.loads(next((public / "g").rglob("catalog.json")).read_text())
        self.assertEqual(private_catalog["record_count"], 23)
        self.assertEqual(private_catalog["event_count"], 78)
        self.assertEqual(public_catalog["record_count"], 1)
        self.assertEqual(public_catalog["event_count"], 2)
        public_aliases = json.loads(next((public / "g").rglob("aliases.json")).read_text())
        self.assertEqual(len(public_aliases["entries"]), 2)  # reviewed UI IDs only; provenance is private
        self.assertEqual(public_aliases["current_entries"], {})
        self.assertEqual(len(public_aliases["paths"]), 1)
        self.assertNotIn("migration/legacy", "".join(file_hashes(public)))
        # No source archive or historical private snapshot may be deployed.
        for p in (public / "g").rglob("*"):
            self.assertNotIn("migration/legacy", p.as_posix())


if __name__ == "__main__":
    unittest.main()
