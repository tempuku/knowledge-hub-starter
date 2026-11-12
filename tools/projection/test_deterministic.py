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

    def test_invalid_staging_path(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(projection.ProjectionError):
                projection.write_staging(Path(directory) / "stage", {"../leak.json": b"x"})


if __name__ == "__main__":
    unittest.main()
