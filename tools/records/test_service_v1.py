"""Disposable Git integration tests for the W-02 service.

The fixtures use actual Git commits and worktrees, never mocked commit results.
"""
import subprocess
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from service_v1 import GitRecordWriter
from writer_v1 import WriterError
from validate_v1 import parse_log, repository


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


class ServiceFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.name", "Fixture")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        (self.root / "openwiki").mkdir()
        (self.root / "openwiki/index.md").write_text(
            '---\nokf_version: "0.2"\n---\n\n# Knowledge Hub\n\n',
            encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "initial")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.capability = {"repository_mode": "private",
                           "operations": ["create", "update"],
                           "publisher_scope": False}
        self.writer = GitRecordWriter(self.root, self.capability)
        self.path = "openwiki/notes/sample.md"
        self.source = '---\ntype: note\ntitle: "Sample"\n---\n\nBody\n'
        self.request = {
            "command": "create", "idempotency_key": str(uuid.uuid4()),
            "actor": {"id": "test", "kind": "agent", "label": "Test agent"},
            "summary": "Create sample", "expected_head": self.head,
            "path": self.path, "content": self.source,
        }

    def create(self):
        return self.writer.write(self.request)

    def test_create_read_update_and_retry(self):
        first = self.create()
        self.assertEqual(first["status"], "committed")
        self.assertEqual(first["publication"], "pending")
        self.assertNotEqual(first["head"], self.head)
        self.assertEqual(first["head"], git(self.root, "rev-parse", "main"))
        read = self.writer.read(first["record_id"])
        self.assertEqual(read["version"], first["event_id"])
        self.assertEqual(read["head"], first["head"])
        self.assertEqual(self.writer.write(self.request),
                         {**first, "status": "already_committed"})
        updated = read["content"].replace("Body\n", "New body\n")
        second = self.writer.write({
            **{k: v for k, v in self.request.items() if k != "path"}, "command": "update", "record_id": first["record_id"],
            "expected_version": first["event_id"], "expected_head": first["head"],
            "content": updated,
        } | {"idempotency_key": str(uuid.uuid4())})
        self.assertEqual(second["status"], "committed")
        self.assertEqual(self.writer.read(first["record_id"])["content"], updated)
        events = parse_log(subprocess.check_output(
            ["git", "show", "main:" + self.path[:-3] + ".log.md"], cwd=self.root),
            self.path)
        self.assertEqual([e["sequence"] for e in events], [1, 2])
        with tempfile.TemporaryDirectory() as checkout:
            git(self.root, "worktree", "add", "--detach", checkout, second["head"])
            try:
                self.assertEqual(repository(Path(checkout), base=self.head)["events"], 2)
            finally:
                git(self.root, "worktree", "remove", "--force", checkout)

    def test_same_key_changed_request_and_stale_head(self):
        first = self.create()
        with self.assertRaises(WriterError) as err:
            self.writer.write({**self.request, "summary": "Changed"})
        self.assertEqual(err.exception.code, "IDEMPOTENCY_CONFLICT")
        with self.assertRaises(WriterError) as err:
            self.writer.write({**self.request, "idempotency_key": str(uuid.uuid4())})
        self.assertEqual(err.exception.code, "CONFLICT")
        self.assertEqual(git(self.root, "rev-parse", "main"), first["head"])

    def test_public_default_private_denied(self):
        public = GitRecordWriter(self.root, {**self.capability,
                                             "repository_mode": "public",
                                             "publisher_scope": True})
        with self.assertRaises(WriterError) as err:
            public.write(self.request)
        self.assertEqual(err.exception.code, "PUBLICATION_DENIED")
        self.assertEqual(git(self.root, "rev-parse", "main"), self.head)

    def test_fault_before_publication_keeps_branch(self):
        for failure in ("staged", "validated", "committed"):
            with self.subTest(failure=failure):
                def fail(point):
                    if point == failure:
                        raise RuntimeError("Injected failure")
                writer = GitRecordWriter(self.root, self.capability, fault=fail)
                with self.assertRaises(RuntimeError):
                    writer.write(self.request)
                self.assertEqual(git(self.root, "rev-parse", "main"), self.head)

    def test_duplicate_titles_and_eight_level_hierarchy(self):
        first = self.create()
        second_path = "openwiki/ideas/a/b/c/d/e/f/g/another.md"
        result = self.writer.write({
            **self.request, "idempotency_key": str(uuid.uuid4()),
            "expected_head": first["head"], "path": second_path,
        })
        self.assertNotEqual(first["record_id"], result["record_id"])
        self.assertNotEqual(first["event_id"], result["event_id"])
        self.assertEqual(self.writer.read(result["record_id"])["path"], second_path)
        self.assertEqual(git(self.root, "rev-parse", "main"), result["head"])

    def test_stale_version_and_no_change_do_not_commit(self):
        first = self.create()
        original = self.writer.read(first["record_id"])["content"]
        update = {
            **{k: v for k, v in self.request.items() if k != "path"}, "command": "update",
            "record_id": first["record_id"], "expected_version": first["event_id"],
            "expected_head": first["head"], "content": original,
            "idempotency_key": str(uuid.uuid4()),
        }
        with self.assertRaises(WriterError) as err:
            self.writer.write(update)
        self.assertEqual(err.exception.code, "NO_CHANGE")
        with self.assertRaises(WriterError) as err:
            self.writer.write({
                **update, "content": original.replace("Body\n", "Changed\n"),
                "expected_version": str(uuid.uuid4()),
            })
        self.assertEqual(err.exception.code, "CONFLICT")
        self.assertEqual(git(self.root, "rev-parse", "main"), first["head"])

    def test_clock_skew_rejects_update(self):
        first = self.create()
        source = self.writer.read(first["record_id"])["content"]
        past = GitRecordWriter(self.root, self.capability,
                               clock=lambda: datetime(2000, 1, 1, tzinfo=timezone.utc))
        with self.assertRaises(WriterError) as err:
            past.write({
                **{k: v for k, v in self.request.items() if k != "path"}, "command": "update",
                "record_id": first["record_id"],
                "expected_version": first["event_id"],
                "expected_head": first["head"],
                "idempotency_key": str(uuid.uuid4()),
                "content": source.replace("Body\n", "Different\n"),
            })
        self.assertEqual(err.exception.code, "CLOCK_SKEW")
        self.assertEqual(git(self.root, "rev-parse", "main"), first["head"])


if __name__ == "__main__":
    unittest.main()
