"""Contract test for the read-only frozen Git candidate report adapter."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import report_v1
from reconcile_v1 import ReconciliationError


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class CandidateReportTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.source = b"---\ntype: note\ntitle: Old\n---\n\nUnique\n"
        self.archive = b"# Legacy event evidence\n"
        self.base = "b" * 40
        self.candidate = "c" * 40
        self.review = {
            "schema_version": 1, "review_status": "reviewed-for-dry-run",
            "base_revision": self.base,
            "items": [
                {"old_path": "openwiki/notes/old.md", "disposition": "record",
                 "allocated_record_id": "r1", "destination_path": "openwiki/notes/new.md",
                 "source_sha256": digest(self.source)},
                {"old_path": "openwiki/notes/old.log.md", "disposition": "structural",
                 "source_sha256": digest(self.archive)}
            ],
            "legacy_event_mappings": [],
            "normalization_event_allocations": [],
            "imported_baseline_allocations": [],
            "legacy_ui_mappings": [],
        }
        self.records = [{"id": "r1", "path": "openwiki/notes/new.md"}]
        self.histories = {"r1": [{"id": "e1", "record_id": "r1",
                                 "before": None, "after": self.source.decode()}]}
        self.review_bytes = json.dumps(self.review, sort_keys=True).encode()

    def fake_git(self, _root, *args):
        if args == ("show", self.candidate + ":migration/records-v1.json"):
            return self.review_bytes
        if args == ("show", self.base + ":openwiki/notes/old.md"):
            return self.source
        if args == ("show", self.base + ":openwiki/notes/old.log.md"):
            return self.archive
        if args == ("ls-tree", "-r", "--name-only", "-z", self.candidate,
                    "--", "migration/legacy"):
            return b"migration/legacy/log.md\0"
        if args == ("show", self.candidate + ":migration/legacy/log.md"):
            return self.archive
        raise AssertionError("Unexpected Git access " + str(args))

    def test_candidate_report_only_emits_pinned_proof_and_counts(self):
        with patch.object(report_v1, "load_revision",
                          return_value=(self.candidate, "d"*40, self.records,
                                        self.histories, {})):
            with patch.object(report_v1, "git_bytes", side_effect=self.fake_git):
                evidence = report_v1.report(self.root.name, self.candidate)
        self.assertEqual(evidence["source_revision"], self.candidate)
        self.assertEqual(evidence["reviewed_base_revision"], self.base)
        self.assertEqual(evidence["sources_checked"], 2)
        self.assertEqual(evidence["archive_copies_verified"], 1)
        self.assertEqual(evidence["reviewed_manifest_sha256"], digest(self.review_bytes))
        self.assertNotIn("Unique", str(evidence))
        self.assertNotIn("Legacy event", str(evidence))

    def test_missing_archive_evidence_fails_closed(self):
        def altered(_root, *args):
            if args and args[0] == "ls-tree":
                return b""
            return self.fake_git(_root, *args)
        with patch.object(report_v1, "load_revision",
                          return_value=(self.candidate, "d"*40, self.records,
                                        self.histories, {})):
            with patch.object(report_v1, "git_bytes", side_effect=altered):
                with self.assertRaisesRegex(ReconciliationError, "not archived"):
                    report_v1.report(self.root.name, self.candidate)


if __name__ == "__main__":
    unittest.main()
