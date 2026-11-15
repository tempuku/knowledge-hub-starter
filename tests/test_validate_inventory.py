"""Regression and fail-closed tests for reviewed issue #35 manifests."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_inventory import ROOT, validate


MANIFEST = ROOT / "migration/records-v1.json"


class ReviewedInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def errors(self, mutate):
        candidate = copy.deepcopy(self.manifest)
        mutate(candidate)
        return validate(candidate, ROOT)

    def test_reviewed_manifest_covers_actual_frozen_repository(self):
        self.assertEqual([], validate(self.manifest, ROOT))
        self.assertEqual(45, len(self.manifest["items"]))
        self.assertEqual(52, len(self.manifest["legacy_event_mappings"]))
        self.assertEqual(61, len(self.manifest["legacy_ui_mappings"]))

    def test_generator_check_validates_reviewed_file_without_rewriting(self):
        before = MANIFEST.read_bytes()
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/inventory_legacy.py"),
             "--revision", self.manifest["base_revision"], "--check"],
            cwd=ROOT, text=True, capture_output=True, check=True)
        self.assertIn("reviewed manifest reconciles", result.stdout)
        self.assertEqual(before, MANIFEST.read_bytes())

    def test_missing_source_fails_exact_coverage(self):
        errors = self.errors(lambda d: d["items"].pop())
        self.assertTrue(any("inventory omits frozen sources" in error for error in errors))

    def test_source_hash_tampering_fails(self):
        errors = self.errors(lambda d: d["items"][0].update(source_sha256="0" * 64))
        self.assertTrue(any("source_sha256 does not match" in error for error in errors))

    def test_invalid_record_uuid_fails(self):
        errors = self.errors(lambda d: next(i for i in d["items"] if i["disposition"] == "record").update(allocated_record_id="not-a-uuid"))
        self.assertTrue(any("stable UUIDv4 allocated_record_id" in error for error in errors))

    def test_casefold_destination_collision_fails(self):
        def mutate(data):
            records = [i for i in data["items"] if i["disposition"] == "record"]
            records[1]["destination_path"] = records[0]["destination_path"].upper()
        errors = self.errors(mutate)
        self.assertTrue(any("case-fold collision" in error or "collides with target" in error for error in errors))

    def test_reserved_destination_path_fails(self):
        errors = self.errors(lambda d: next(i for i in d["items"] if i["disposition"] == "record").update(
            destination_path="openwiki/notes/con.md"))
        self.assertTrue(any("safe explicit destination_path" in error for error in errors))

    def test_uppercase_uuid_fails_canonical_uuidv4(self):
        def mutate(data):
            record = next(i for i in data["items"] if i["disposition"] == "record")
            record["allocated_record_id"] = record["allocated_record_id"].upper()
        errors = self.errors(mutate)
        self.assertTrue(any("stable UUIDv4 allocated_record_id" in error for error in errors))

    def test_boolean_schema_version_fails(self):
        errors = self.errors(lambda d: d.update(schema_version=True))
        self.assertTrue(any("schema_version must be integer 1" in error for error in errors))

    def test_missing_source_hash_fails(self):
        errors = self.errors(lambda d: d["items"][0].update(source_sha256=None))
        self.assertTrue(any("source_sha256 must be an explicit lowercase" in error for error in errors))

    def test_private_event_cannot_be_added_to_public_allowlist(self):
        def mutate(data):
            private = next(m for m in data["legacy_event_mappings"]
                           if m["source_actor"] and m["legacy_event_id"] != "demo-native-update-20261110")
            data["publication_eligibility"]["record_ids"].append(private["record_id"])
            data["publication_eligibility"]["event_ids"].append(private["allocated_event_id"])
        errors = self.errors(mutate)
        self.assertTrue(any("not currently mapped public" in error or "non-public legacy visibility" in error
                            for error in errors))

    def test_legacy_missing_visibility_cannot_be_widened(self):
        def mutate(data):
            item = next(i for i in data["items"] if i["old_path"] == "openwiki/CI.md")
            item["metadata_mapping"]["visibility"] = "public"
        errors = self.errors(mutate)
        self.assertTrue(any("missing legacy visibility defaults to private" in error for error in errors))

    def test_unknown_legacy_event_mapping_fails(self):
        def mutate(data):
            entry = copy.deepcopy(data["legacy_event_mappings"][0])
            entry["legacy_event_id"] = "forged-event-id"
            entry["source_ref"] = f"{entry['log_path']}#forged-event-id"
            data["legacy_event_mappings"].append(entry)
        errors = self.errors(mutate)
        self.assertTrue(any("does not resolve to an actual event" in error for error in errors))

    def test_duplicate_legacy_operation_allocation_fails(self):
        def mutate(data):
            data["legacy_event_mappings"][1]["allocated_operation_id"] = data["legacy_event_mappings"][0]["allocated_operation_id"]
        errors = self.errors(mutate)
        self.assertTrue(any("allocated_operation_id must be a unique" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
