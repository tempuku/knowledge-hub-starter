"""Record projection tests: stable order, byte guards and pagination."""
import json
import unittest

from deterministic import ProjectionError
from record_pages import build_record_pages


def record(rid, title, content="hello\n"):
    return {"id": rid, "title": title, "description": "", "type": "note",
            "status": "draft", "project_id": "project", "tags": [],
            "area": "notes", "updated_at": "2026-11-12T12:00:00Z",
            "version": 1, "content_bytes": len(content.encode("utf-8")),
            "content": content, "path": f"openwiki/notes/{rid}.md"}


class RecordPageTests(unittest.TestCase):
    def test_stable_sort_and_detail_size(self):
        rows = [record("b", "zeta"), record("a", "Älpha"), record("c", "alpha")]
        first = build_record_pages(rows)
        self.assertEqual(first, build_record_pages(list(reversed(rows))))
        items = json.loads(first["records/catalog/1.json"])["items"]
        self.assertEqual([item['id'] for item in items], ["c", "b", "a"])
        for item in items:
            self.assertEqual(item["detail_bytes"], len(first[f'records/{item['id']}.json']))
            self.assertEqual(json.loads(first[f'records/{item['id']}.meta.json"])["detail_bytes"],
                             item["detail_bytes"])
            self.assertNotIn("detail_bytes", json.loads(first[f'records/{item['id']}.json"]))

    def test_pagination_51_records(self):
        rows = [record(f"r{i:03}", f"Title {i:03}") for i in range(51)]
        files = build_record_pages(rows)
        index = json.loads(files["records/catalog/index.json"])
        self.assertEqual([p["count"] for p in index["pages"]], [50, 1])
        self.assertEqual(index["record_count"], 51)

    def test_duplicate_and_bad_byte_count_rejected(self):
        a = record("same", "A")
        for rows in ([a, a], [{**a, "content_bytes": 0}]):
            with self.assertRaises(ProjectionError):
                build_record_pages(rows)

    def test_utf8_byte_size(self):
        files = build_record_pages([record("unicode", "Café", "東京\n")])
        detail = json.loads(files["records/unicode.json"])
        self.assertEqual(detail["content_bytes"], len("東京\n".encode("utf-8")))


if __name__ == "__main__":
    unittest.main()
