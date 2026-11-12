"""Publication safety tests for the opt-in projection entrypoint."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build import publish
from deterministic import ProjectionError


class PublicationTests(unittest.TestCase):
    def test_public_mode_fails_closed_before_loading_source(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "data"
            with self.assertRaises(ProjectionError):
                publish(Path(directory), destination, "HEAD", mode="public")
            self.assertFalse(destination.exists())

    def test_private_manifest_is_switched_only_after_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "data"
            record = {"id": "r1", "title": "A", "description": "",
                      "type": "note", "status": "draft", "project_id": None,
                      "tags": [], "area": "notes", "updated_at": "2026-11-12T12:00:00Z",
                      "version": 1, "content_bytes": 2, "content": "a\n",
                      "path": "openwiki/notes/a.md"}
            event = {"id": "e1", "record_id": "r1", "sequence": 1,
                     "recorded_at": "2026-11-12T12:00:00Z", "before": None,
                     "after": "a\n", "path_before": None, "path_after": record["path"]}
            summary = {"id": "e1", "record_id": "r1", "sequence": 1,
                       "recorded_at": event["recorded_at"]}
            with patch("build.load_revision", return_value=("c" * 40, "a" * 40,
                    [record], {"r1": [event]}, {"e1": summary})):
                manifest = publish(Path(directory), destination, "HEAD")
                self.assertTrue((destination / "g" / manifest["generation"] / "catalog.json").exists())
                self.assertTrue((destination / "manifest.json").exists())
                with self.assertRaises(ProjectionError):
                    publish(Path(directory), destination, "HEAD")
            self.assertEqual(manifest["mode"], "private")


if __name__ == "__main__":
    unittest.main()
