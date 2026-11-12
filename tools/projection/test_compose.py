"""Integration fixtures for deterministic P-02 composition."""
import json
import unittest

from compose import build_projection
from deterministic import ProjectionError


def fixture():
    record = {"id": "r1", "title": "Example", "description": "Description",
              "type": "note", "status": "draft", "project_id": None,
              "tags": ["example"], "area": "notes",
              "updated_at": "2026-11-12T12:00:00Z", "version": 1,
              "content_bytes": 6, "content": "hello\n",
              "path": "openwiki/notes/example.md",
              "reminders": [["2026-12-01", "Review"]]}
    event = {"id": "e1", "record_id": "r1", "sequence": 1,
             "recorded_at": "2026-11-12T12:00:00Z",
             "before": None, "after": "hello\n", "path_before": None,
             "path_after": record["path"]}
    summary = {"id": "e1", "record_id": "r1", "sequence": 1,
               "recorded_at": event["recorded_at"]}
    return [record], {"r1": [event]}, {"e1": summary}


class CompositionTests(unittest.TestCase):
    def test_complete_generation_deterministic(self):
        args = fixture()
        files = build_projection(*args)
        self.assertEqual(files, build_projection(*args))
        for path in ("catalog.json", "calendar/2026.json",
                     "days/2026-11-12/index.json", "history/r1/index.json",
                     "records/r1.json", "records/r1.meta.json",
                     "events/e1.json", "events/e1.meta.json",
                     "reminders/2026-12.json", "search/manifest.json",
                     "aliases.json", "records/catalog/index.json"):
            self.assertIn(path, files)
            self.assertTrue(files[path].endswith(b"\n"))
        self.assertEqual(json.loads(files["catalog.json"])["event_count"], 1)

    def test_missing_history_and_summary_rejected(self):
        records, histories, summaries = fixture()
        with self.assertRaises(ProjectionError):
            build_projection(records, {}, summaries)
        with self.assertRaises(ProjectionError):
            build_projection(records, histories, {})


if __name__ == "__main__":
    unittest.main()
