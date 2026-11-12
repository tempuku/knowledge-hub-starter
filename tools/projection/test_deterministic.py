"""Regression tests for #31 deterministic projection primitives."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("deterministic.py")
spec = importlib.util.spec_from_file_location("projection_deterministic", MODULE)
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


class DeterministicProjectionTests(unittest.TestCase):
    def test_generation_changes_with_policy(self):
        self.assertEqual(projection.generation_id("tree", "v1", "public"), projection.generation_id("tree", "v1", "public"))
        self.assertNotEqual(projection.generation_id("tree", "v1", "public"), projection.generation_id("tree", "v1", "private"))

    def test_json_utf8_and_trailing_newline(self):
        self.assertEqual(projection.json_bytes({"schema_version": 1, "title": "Été"}), b'{\n  "schema_version": 1,\n  "title": "\xc3\x89t\xc3\xa9"\n}\n')

    def test_pagination_51_events(self):
        items = [{"id": str(i)} for i in range(51)]
        pages = projection.paginate(items, event_summaries=True)
        self.assertEqual(len(pages), 2)
        self.assertIn(b'"next": 2', pages[0])
        self.assertIn(b'"next": null', pages[1])

    def test_pagination_byte_budget(self):
        items = [{"id": str(i), "summary": "a" * 9000} for i in range(40)]
        pages = projection.paginate(items, event_summaries=True)
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(page) <= projection.PAGE_BYTES for page in pages))

    def test_search_independent_of_record_order(self):
        records = [
            {"id": "b", "title": "Café Notes", "tags": ["plan"], "body": "Roadmap"},
            {"id": "a", "title": "Project", "description": "CAFÉ", "body": "Notes"},
        ]
        self.assertEqual(projection.search_shards(records), projection.search_shards(list(reversed(records))))
        self.assertEqual(projection.tokenize("CAFÉ café"), ["café", "café"])


    def test_query_and_ranking_filters(self):
        records = [
            {"id": "a", "title": "Blue Harbor", "description": "", "tags": ["blue"],
             "body": "", "status": "stable", "area": "notes/a", "type": "note",
             "updated_at": "2026-01-01T00:00:00Z"},
            {"id": "b", "title": "Harbor", "description": "blue", "tags": [],
             "body": "", "status": "stable", "area": "notes/b", "type": "note",
             "updated_at": "2026-02-01T00:00:00Z"},
            {"id": "c", "title": "Blue Harbor", "description": "", "tags": [],
             "body": "", "status": "deprecated", "area": "archive", "type": "note",
             "updated_at": "2026-03-01T00:00:00Z"},
        ]
        shards = projection.search_shards(records)
        self.assertEqual(projection.query_search("blue harbor", records, shards), ["a", "b"])
        self.assertEqual(projection.query_search("blue harbor", records, shards, include_archived=True), ["c", "a", "b"])
        self.assertEqual(projection.query_search("blue harbor", records, shards, area="notes"), ["a", "b"])
        self.assertEqual(projection.query_search("blue harbor", records, shards, tag="blue"), ["a"])
        self.assertEqual(projection.query_search("missing harbor", records, shards), [])
        with self.assertRaises(projection.ProjectionError):
            projection.query_search("aa bb cc dd ee ff gg hh ii", records, shards)

    def test_invalid_staging_path(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(projection.ProjectionError):
                projection.write_staging(Path(directory) / "stage", {"../leak.json": b"x"})

    def test_staging_rejects_path_collisions_without_creating_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            with self.assertRaises(projection.ProjectionError):
                projection.write_staging(stage, {"a.json": b"1", "A.json": b"2"})
            self.assertFalse(stage.exists())
            with self.assertRaises(projection.ProjectionError):
                projection.write_staging(stage, {"a": b"1", "a/b": b"2"})
            self.assertFalse(stage.exists())

    def test_staging_rejects_windows_and_dot_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in ("a\\\\b", "./a", "a/../b"):
                stage = Path(directory) / "stage"
                with self.assertRaises(projection.ProjectionError):
                    projection.write_staging(stage, {path: b"1"})
                self.assertFalse(stage.exists())

    def test_staging_writes_valid_nested_files(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            projection.write_staging(stage, {"days/2026-11-12/1.json": b"{}\\n"})
            self.assertEqual((stage / "days/2026-11-12/1.json").read_bytes(), b"{}\\n")


if __name__ == "__main__":
    unittest.main()
