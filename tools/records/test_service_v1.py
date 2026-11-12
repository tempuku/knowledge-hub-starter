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
                           "operations": ["read", "create", "update"],
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

    def test_read_denies_untrusted_and_unauthorized_context(self):
        first = self.create()
        for capability in ({}, {
            "repository_mode": "private", "operations": ["update"],
            "publisher_scope": False,
        }, {
            "repository_mode": "unknown", "operations": ["read"],
            "publisher_scope": False,
        }):
            with self.subTest(capability=capability):
                denied = GitRecordWriter(self.root, capability)
                with self.assertRaises(WriterError) as error:
                    denied.read(first["record_id"])
                self.assertEqual(error.exception.code, "NOT_FOUND")
        public = GitRecordWriter(self.root, {
            "repository_mode": "public", "operations": ["read"],
            "publisher_scope": False,
        })
        with self.assertRaises(WriterError) as error:
            public.read(first["record_id"])
        self.assertEqual(error.exception.code, "NOT_FOUND")

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



    def test_two_updates_same_recorded_second(self):
        """S1/S2: sequence (rather than timestamp) orders all revisions."""
        first = self.create()
        original = self.writer.read(first["record_id"])["content"]
        prior_log = subprocess.check_output(
            ["git", "show", "main:" + self.path[:-3] + ".log.md"], cwd=self.root)
        recorded = parse_log(prior_log, self.path)[0]["recorded_at"]
        timestamp = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
        fixed = GitRecordWriter(self.root, self.capability, clock=lambda: timestamp)
        results = [first]
        for number in (1, 2):
            request = {
                **{k: v for k, v in self.request.items() if k != "path"},
                "command": "update",
                "record_id": first["record_id"],
                "expected_head": results[-1]["head"],
                "expected_version": results[-1]["event_id"],
                "idempotency_key": str(uuid.uuid4()),
                "content": original.replace("Body\n", f"Revision {number}\n"),
            }
            results.append(fixed.write(request))
        log = subprocess.check_output(
            ["git", "show", "main:" + self.path[:-3] + ".log.md"], cwd=self.root)
        events = parse_log(log, self.path)
        self.assertEqual([e["sequence"] for e in events], [1, 2, 3])
        self.assertEqual([e["recorded_at"] for e in events], [recorded] * 3)
        self.assertEqual(len({e["id"] for e in events}), 3)
        self.assertEqual(len({e["operation_id"] for e in events}), 3)
        self.assertEqual(events[-1]["after"], self.writer.read(first["record_id"])["content"])
        self.assertEqual(events[1]["before"], events[0]["after"])
        self.assertEqual(events[2]["before"], events[1]["after"])

    def test_lost_response_after_cas_recovers_original_commit(self):
        """S8/S11: a crash after ref publication has a durable log receipt."""
        def lose_response(point):
            if point == "published":
                raise ConnectionError("Injected response loss after CAS")
        writer = GitRecordWriter(self.root, self.capability, fault=lose_response)
        with self.assertRaises(ConnectionError):
            writer.write(self.request)
        original_commit = git(self.root, "rev-parse", "refs/heads/main")
        self.assertNotEqual(original_commit, self.head)
        recovered = self.writer.write(self.request)
        self.assertEqual(recovered["status"], "already_committed")
        self.assertEqual(recovered["head"], original_commit)
        self.assertEqual(git(self.root, "rev-parse", "refs/heads/main"), original_commit)
        self.assertEqual(len(git(self.root, "rev-list", "refs/heads/main").splitlines()), 2)

    def test_remote_cas_receipt_survives_lost_local_ref_update(self):
        """S8/S11: remote publication is authoritative despite a stale clone."""
        with tempfile.TemporaryDirectory() as temp:
            origin = Path(temp) / "origin.git"
            checkout = Path(temp) / "client"
            subprocess.run(["git", "clone", "--quiet", "--bare",
                            str(self.root), str(origin)], check=True)
            subprocess.run(["git", "clone", "--quiet", "--branch", "main",
                            str(origin), str(checkout)], check=True)
            base = git(checkout, "rev-parse", "refs/heads/main")
            request = {**self.request, "expected_head": base}

            def lose_local_ref(point):
                if point == "remote_published":
                    raise ConnectionError("Injected failure after remote CAS")
            faulty = GitRecordWriter(checkout, self.capability,
                                     remote="origin", fault=lose_local_ref)
            with self.assertRaises(ConnectionError):
                faulty.write(request)
            remote_commit = git(origin, "rev-parse", "refs/heads/main")
            self.assertNotEqual(remote_commit, base)
            self.assertEqual(git(checkout, "rev-parse", "refs/heads/main"), base)
            recovered = GitRecordWriter(checkout, self.capability,
                                        remote="origin").write(request)
            self.assertEqual(recovered["status"], "already_committed")
            self.assertEqual(recovered["head"], remote_commit)
            self.assertEqual(git(origin, "rev-parse", "refs/heads/main"), remote_commit)
            self.assertEqual(git(checkout, "rev-parse", "refs/heads/main"), base)

    def test_remote_cas_rejects_second_independent_clone(self):
        """S10: only one clone can advance a shared remote from the same base."""
        with tempfile.TemporaryDirectory() as temp:
            origin = Path(temp) / "origin.git"
            a, b = Path(temp) / "a", Path(temp) / "b"
            subprocess.run(["git", "clone", "--quiet", "--bare",
                            str(self.root), str(origin)], check=True)
            for clone in (a, b):
                subprocess.run(["git", "clone", "--quiet", "--branch", "main",
                                str(origin), str(clone)], check=True)
            base = git(a, "rev-parse", "refs/heads/main")
            self.assertEqual(base, git(b, "rev-parse", "refs/heads/main"))
            writer_a = GitRecordWriter(a, self.capability, remote="origin")
            writer_b = GitRecordWriter(b, self.capability, remote="origin")
            request = {**self.request, "expected_head": base}
            winner = writer_a.write(request)
            with self.assertRaises(WriterError) as failure:
                writer_b.write({**request, "idempotency_key": str(uuid.uuid4())})
            self.assertEqual(failure.exception.code, "CONFLICT")
            self.assertEqual(git(origin, "rev-parse", "refs/heads/main"), winner["head"])
            self.assertEqual(git(b, "rev-parse", "refs/heads/main"), base)
            self.assertEqual(writer_a.read(winner["record_id"])["head"], winner["head"])

if __name__ == "__main__":
    unittest.main()
