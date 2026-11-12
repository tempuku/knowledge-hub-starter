"""Contract-first fixtures for the #28 domain writer primitives.

Full disposable-Git commit/CAS/failure-injection acceptance follows in #28;
these tests must never be represented as completing that issue.
"""
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_v1 as v1
import writer_v1 as writer


def uid():
    return str(uuid.uuid4())


class WriterPrimitiveFixtures(unittest.TestCase):
    def setUp(self):
        self.record_id = uid()
        self.event_id = uid()
        self.operation_id = uid()
        self.key = uid()
        self.path = "openwiki/notes/sample.md"
        self.source = (
            "---\n"
            "type: note\n"
            "title: \"Test record\"\n"
            "---\n\nBody\n"
        )
        self.request = {
            "command": "create", "idempotency_key": self.key,
            "actor": {"id": "local-agent", "kind": "agent", "label": "Local test"},
            "summary": "Create test record",
            "expected_head": "a" * 40,
            "path": self.path, "content": self.source,
        }

    def first(self, at="2026-11-12T08:00:00Z"):
        normalized = writer.normalized_request(self.request)
        after = writer.create_source(self.source, self.record_id)
        event = writer.make_event(
            normalized, record_id=self.record_id, event_id=self.event_id,
            operation_id=self.operation_id, sequence=1, action="CREATED",
            path_before=None, path_after=self.path, before=None, after=after,
            previous_event_id=None, recorded_at=at,
        )
        return after, event

    def test_canonical_digest_optional_fields(self):
        implicit = writer.normalized_request(self.request)
        explicit = writer.normalized_request({
            **self.request, "occurred_on": None, "occurred_at": None,
            "publish_current": False,
        })
        self.assertEqual(writer.request_digest(implicit),
                         writer.request_digest(explicit))
        self.assertEqual(len(writer.request_digest(implicit)), 64)
        self.assertNotIn("idempotency_key",
                         json.dumps({k: v for k, v in implicit.items()
                                     if k != "idempotency_key"}))

    def test_digest_changes_with_request_semantics(self):
        original = writer.request_digest(writer.normalized_request(self.request))
        amended = {**self.request, "content": self.source.replace("Body", "Change")}
        self.assertNotEqual(original,
                            writer.request_digest(writer.normalized_request(amended)))
        amended = {**self.request, "actor": {
            "id": "other-agent", "kind": "agent", "label": "Local test"}}
        self.assertNotEqual(original,
                            writer.request_digest(writer.normalized_request(amended)))

    def test_strict_shape_and_no_float(self):
        for bad in (
            {**self.request, "unexpected_field": "ignored"},
            {**self.request, "publish_current": 1},
            {**self.request, "actor": {"id": "a", "kind": "agent", "label": "a",
                                      "verified_identity": True}},
            {**self.request, "x_sample": 1.5},
            {**self.request, "expected_head": "not-a-commit"},
        ):
            with self.subTest(request=bad), self.assertRaises(writer.WriterError):
                writer.normalized_request(bad)

    def test_generated_ids_and_private_defaults(self):
        result = writer.create_source(self.source, self.record_id)
        meta, text = v1.parse_record(result.encode("utf-8"), "sample.md")
        self.assertEqual(meta["id"], self.record_id)
        self.assertEqual(meta["schema_version"], 1)
        self.assertEqual(meta["visibility"], "private")
        self.assertEqual(meta["status"], "draft")
        self.assertEqual(text.count("\r"), 0)
        self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
        self.assertIn("\n---\n\nBody\n", text)
        for prohibited in ("id: \"" + uid() + "\"\n",
                           "schema_version: 1\n"):
            modified = self.source.replace("type: note\n", prohibited + "type: note\n")
            with self.subTest(prohibited=prohibited), self.assertRaises(writer.WriterError):
                writer.create_source(modified, self.record_id)

    def test_append_uses_exact_log_prefix(self):
        after, event = self.first()
        log = writer.append_log(None, event)
        self.assertEqual(v1.parse_log(log.encode(), "log"), [event])
        new_source = after.replace("Body\n", "Changed body\n")
        self.request = {
            **self.request, "command": "update", "record_id": self.record_id,
            "expected_version": self.event_id, "content": new_source,
        }
        self.request.pop("path")
        next_event = writer.make_event(
            writer.normalized_request(self.request),
            record_id=self.record_id, event_id=uid(), operation_id=uid(),
            sequence=2, action="UPDATED", path_before=self.path,
            path_after=self.path, before=after, after=new_source,
            previous_event_id=self.event_id,
            recorded_at=event["recorded_at"],
        )
        appended = writer.append_log(log, next_event)
        self.assertTrue(appended.startswith(log))
        self.assertEqual(len(v1.parse_log(appended.encode(), "log")), 2)
        v1.validate_chain([event, next_event], self.path,
                          v1.parse_record(new_source.encode(), self.path)[0],
                          new_source, set())

    def test_real_git_validator_accepts_generated_files(self):
        after, event = self.first()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.invalid"],
                           cwd=root, check=True)
            files = {
                self.path: after,
                self.path[:-3] + ".log.md": writer.append_log(None, event),
                "openwiki/index.md": (
                    '---\nokf_version: "0.2"\n---\n\n'
                    '# Root\n\n* [Notes](notes/)\n'
                ),
                "openwiki/notes/index.md": "# Notes\n\n* [Sample](sample.md)\n",
            }
            for path, text in files.items():
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(text, encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            self.assertEqual(v1.repository(root, strict_indexes=True),
                             {"records": 1, "events": 1})


if __name__ == "__main__":
    unittest.main()
