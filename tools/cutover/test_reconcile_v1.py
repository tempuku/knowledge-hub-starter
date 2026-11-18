"""Fail-closed reviewed inventory and exact history allocation tests."""
import copy
import hashlib
import unittest

from reconcile_v1 import ReconciliationError, reconcile


def sha(b):
    return hashlib.sha256(b).hexdigest()


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.raw = b"---\ntype: note\ntitle: Original\n---\n\nUnique text\n"
        self.legacy = b"# Old log\n\nUnedited evidence\n"
        self.source = {"openwiki/notes/original.md": self.raw,
                       "openwiki/notes/original.log.md": self.legacy}
        self.archives = {sha(self.legacy)}
        self.records = [{"id": "r1", "path": "openwiki/notes/normalized.md"}]
        self.history = {"r1": [
            {"id": "e1", "record_id": "r1", "sequence": 1, "action": "CREATED",
             "before": None, "after": self.raw.decode(),
             "operation_id": "o1", "idempotency_key": "k1",
             "provenance": {"kind": "legacy-log", "source_ref": "original#old", "original_time": None}},
            {"id": "e2", "record_id": "r1", "sequence": 2, "action": "IMPORTED",
             "before": self.raw.decode(), "after": "normalized",
             "operation_id": "o2", "idempotency_key": "k2",
             "provenance": {"kind": "legacy-log", "source_ref": "original", "original_time": None}},
        ]}
        self.manifest = {
            "schema_version": 1, "review_status": "reviewed-for-dry-run",
            "items": [
                {"old_path": "openwiki/notes/original.md", "disposition": "record",
                 "allocated_record_id": "r1", "destination_path": "openwiki/notes/normalized.md",
                 "source_sha256": sha(self.raw)},
                {"old_path": "openwiki/notes/original.log.md", "disposition": "structural",
                 "source_sha256": sha(self.legacy)},
            ],
            "legacy_event_mappings": [
                {"record_id": "r1", "allocated_event_id": "e1",
                 "target_sequence": 1, "allocated_operation_id": "o1",
                 "allocated_idempotency_key": "k1",
                 "provenance_kind": "legacy-log", "source_ref": "original#old",
                 "original_time": None}
            ],
            "normalization_event_allocations": [
                {"record_id": "r1", "allocated_event_id": "e2",
                 "target_sequence": 2, "allocated_operation_id": "o2",
                 "allocated_idempotency_key": "k2"}
            ],
            "imported_baseline_allocations": [],
            "legacy_ui_mappings": [
                {"legacy_ui_id": "old-entry", "record_id": "r1", "event_id": "e1"}],
        }

    def check(self):
        return reconcile(self.manifest, self.source, self.archives,
                         self.records, self.history)

    def test_exact_preservation_and_mapping(self):
        report = self.check()
        self.assertEqual(report["sources_checked"], 2)
        self.assertEqual(report["snapshots_matched"], 1)
        self.assertEqual(report["legacy_events_mapped"], 1)
        self.assertEqual(report["normalization_events_mapped"], 1)
        self.assertEqual(report["legacy_ui_aliases_checked"], 1)

    def test_legacy_bytes_changed_rejected(self):
        self.source["openwiki/notes/original.md"] += b"tampered"
        with self.assertRaisesRegex(ReconciliationError, "digest mismatch"):
            self.check()

    def test_removed_legacy_log_not_archived_rejected(self):
        self.archives.clear()
        with self.assertRaisesRegex(ReconciliationError, "not archived"):
            self.check()

    def test_unique_original_snapshot_missing_rejected(self):
        self.history["r1"][0]["after"] = "summary-only"
        self.history["r1"][1]["before"] = "summary-only"
        with self.assertRaisesRegex(ReconciliationError, "source bytes lost"):
            self.check()

    def test_allocated_event_missing_rejected(self):
        self.history["r1"].pop(0)
        with self.assertRaisesRegex(ReconciliationError, "missing allocated native"):
            self.check()

    def test_normalization_not_imported_rejected(self):
        self.history["r1"][1]["action"] = "UPDATED"
        with self.assertRaisesRegex(ReconciliationError, "action mismatch"):
            self.check()

    def test_legacy_provenance_changed_rejected(self):
        self.history["r1"][0]["provenance"]["source_ref"] = "invented#new"
        with self.assertRaisesRegex(ReconciliationError, "provenance was lost"):
            self.check()

    def test_legacy_ui_event_mapping_missing_rejected(self):
        self.manifest["legacy_ui_mappings"][0]["event_id"] = "not-in-source"
        with self.assertRaisesRegex(ReconciliationError, "lost event"):
            self.check()

    def test_imported_baseline_must_have_null_before(self):
        self.manifest["imported_baseline_allocations"] = [
            {"record_id": "r1", "allocated_event_id": "e2",
             "target_sequence": 2, "allocated_operation_id": "o2",
             "allocated_idempotency_key": "k2"}]
        with self.assertRaisesRegex(ReconciliationError, "invents prior history"):
            self.check()


if __name__ == "__main__":
    unittest.main()
