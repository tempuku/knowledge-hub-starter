import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "validate_inventory_review.py"
spec = importlib.util.spec_from_file_location("validate_inventory_review", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "schema_version": 1, "base_revision": "a" * 40, "review_status": "approved",
            "items": [{
                "old_path": "openwiki/a.md", "disposition": "record",
                "destination_path": "openwiki/area/a.md",
                "allocated_record_id": "41472c01-62c7-4b80-ad27-4aa1b4888fac",
                "source_sha256": "b" * 64, "legacy_log_path": None,
                "legacy_event_ids": [], "legacy_ui_ids": [],
                "project_mapping": "no-project", "metadata_mapping": {"status": "draft"},
                "occurrence_source": None, "review_notes": "Verified source identity and destination"
            }]
        }

    def test_valid_structural_manifest(self):
        self.assertEqual(module.validate(self.manifest), [])

    def test_pending_and_unreviewed_fail_closed(self):
        self.manifest["review_status"] = "pending"
        self.manifest["items"][0]["disposition"] = None
        self.manifest["items"][0]["review_notes"] = "UNREVIEWED"
        self.assertGreaterEqual(len(module.validate(self.manifest)), 3)

    def test_destination_and_id_collisions(self):
        duplicate = dict(self.manifest["items"][0], old_path="openwiki/b.md")
        self.manifest["items"].append(duplicate)
        errors = " ".join(module.validate(self.manifest))
        self.assertIn("destination collision", errors)
        self.assertIn("record UUID", errors)

    def test_no_unreviewed_publication_by_structure(self):
        self.manifest["items"][0]["metadata_mapping"] = None
        self.assertTrue(any("metadata_mapping" in e for e in module.validate(self.manifest)))

if __name__ == "__main__":
    unittest.main()
