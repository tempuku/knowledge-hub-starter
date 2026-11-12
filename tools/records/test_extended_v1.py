"""Real disposable-Git W-03 acceptance for atomic move, archive and reopen."""
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from service_v1 import GitRecordWriter
from writer_v1 import WriterError
from validate_v1 import parse_log, repository
from links_v1 import resolve_historical_path


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


class LifecycleGitFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.name", "Fixture")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        wiki = self.root / "openwiki"
        wiki.mkdir()
        (wiki / "index.md").write_text(
            '---\nokf_version: "0.2"\n---\n\n# Knowledge Hub\n\n')
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "init")
        self.initial_head = git(self.root, "rev-parse", "HEAD")
        self.capability = {
            "repository_mode": "private",
            "operations": ["read", "create", "update", "move", "archive", "reopen"],
            "publisher_scope": False
        }
        self.writer = GitRecordWriter(
            self.root, self.capability, staged_checker=self.check_staged_okf)

    @staticmethod
    def check_staged_okf(workspace):
        # The installed Node staged OKF checker, run on a real worktree/index.
        script = Path(__file__).resolve().parents[2] / "tools/okf/verify.mjs"
        result = subprocess.run(["node", str(script)], cwd=workspace,
                                capture_output=True, text=True)
        if result.returncode:
            raise AssertionError("Staged OKF failure: " + result.stderr[-900:] +
                                 result.stdout[-900:])

    def request(self, command, **fields):
        return {
            "command": command, "idempotency_key": str(uuid.uuid4()),
            "actor": {"id": "trusted-cli", "kind": "agent", "label": "Test actor"},
            "summary": "Fixture " + command, "expected_head":
                git(self.root, "rev-parse", "refs/heads/main"),
            **fields,
        }

    def create(self, path, body="# Heading\n\nBody\n", title="Record"):
        request = self.request(
            "create", path=path,
            content='---\ntype: note\ntitle: "' + title + '"\n---\n\n' + body)
        return self.writer.write(request)

    def history(self, path):
        source = subprocess.check_output(
            ["git", "show", "main:" + path[:-3] + ".log.md"], cwd=self.root)
        return parse_log(source, path)

    def test_archive_reopen_status_and_visibility(self):
        first = self.create("openwiki/notes/record.md")
        original = self.writer.read(first["record_id"])["content"]
        self.assertEqual(len(self.writer.list_records()), 1)
        archived = self.writer.write(self.request(
            "archive", record_id=first["record_id"],
            expected_version=first["version"]))
        self.assertEqual(self.writer.list_records(), [])
        self.assertEqual(len(self.writer.list_records(include_archived=True)), 1)
        self.assertIn('status: "deprecated"', self.writer.read(first["record_id"])["content"])
        self.assertEqual(self.history("openwiki/notes/record.md")[-1]["action"], "ARCHIVED")
        self.assertEqual(self.history("openwiki/notes/record.md")[0]["after"], original)
        with self.assertRaises(WriterError) as no_change:
            self.writer.write(self.request(
                "archive", record_id=first["record_id"],
                expected_version=archived["version"]))
        self.assertEqual(no_change.exception.code, "NO_CHANGE")
        reopened = self.writer.write(self.request(
            "reopen", record_id=first["record_id"],
            expected_version=archived["version"], status="completed"))
        self.assertEqual(reopened["status"], "committed")
        self.assertEqual(self.writer.list_records()[0]["status"], "completed")
        self.assertIn('status: "completed"', self.writer.read(first["record_id"])["content"])
        events = self.history("openwiki/notes/record.md")
        self.assertEqual([e["action"] for e in events],
                         ["CREATED", "ARCHIVED", "REOPENED"])
        self.assertEqual([e["sequence"] for e in events], [1, 2, 3])
        self.assertEqual(len({e["operation_id"] for e in events}), 3)

    def seed_linked_move(self):
        target = self.create("openwiki/concepts/topic.md", "# Topic\n\nConcept\n")
        source = self.create("openwiki/notes/a/target.md",
                             "# Part\n\n[Topic](../../concepts/topic.md#topic)\n",
                             "Source")
        backlink = self.create("openwiki/ideas/reference.md",
                               "# Reference\n\n[Source](../notes/a/target.md#part)\n",
                               "Backlink")
        return target, source, backlink

    def test_move_links_indexes_and_shared_operation_id(self):
        _, source, backlink = self.seed_linked_move()
        previous_head = git(self.root, "rev-parse", "main")
        req = self.request(
            "move", record_id=source["record_id"],
            expected_version=source["version"],
            destination="openwiki/projects/new.md")
        result = self.writer.write(req)
        self.assertEqual(result["record_id"], source["record_id"])
        self.assertEqual(result["record_url"], "openwiki/projects/new.md")
        self.assertNotEqual(previous_head, result["head"])
        self.assertEqual(git(self.root, "rev-parse", "main"), result["head"])
        self.assertIn("[Topic](../concepts/topic.md#topic)",
                      self.writer.read(source["record_id"])["content"])
        self.assertIn("[Source](../projects/new.md#part)",
                      self.writer.read(backlink["record_id"])["content"])
        self.assertIsNone(
            subprocess.run(["git", "cat-file", "-e",
                            "main:openwiki/notes/a/target.md"], cwd=self.root,
                           capture_output=True).stdout.strip() or None)
        moved = self.history("openwiki/projects/new.md")
        reference = self.history("openwiki/ideas/reference.md")
        self.assertEqual([e["action"] for e in moved], ["CREATED", "MOVED"])
        self.assertEqual([e["action"] for e in reference], ["CREATED", "UPDATED"])
        self.assertEqual(moved[-1]["operation_id"], reference[-1]["operation_id"])
        self.assertEqual(moved[-1]["request_sha256"], reference[-1]["request_sha256"])
        self.assertEqual(moved[-1]["path_before"], "openwiki/notes/a/target.md")
        self.assertEqual(moved[-1]["path_after"], "openwiki/projects/new.md")
        self.assertEqual(self.writer.write(req)["status"], "already_committed")
        self.assertEqual(git(self.root, "rev-parse", "main"), result["head"])
        with tempfile.TemporaryDirectory() as temp:
            git(self.root, "worktree", "add", "--detach", temp, result["head"])
            try:
                repository(Path(temp), base=previous_head, strict_indexes=True)
            finally:
                git(self.root, "worktree", "remove", "--force", temp)
        self.assertFalse((self.root / "openwiki/notes/a/target.md").is_file())
        tree = git(self.root, "ls-tree", "-r", "--name-only", "main")
        self.assertNotIn("openwiki/notes/a/index.md", tree)

    def test_unauthorized_backlink_denies_whole_move(self):
        _, source, backlink = self.seed_linked_move()
        base = git(self.root, "rev-parse", "main")
        restricted = GitRecordWriter(self.root, {
            **self.capability, "writable_record_ids": [source["record_id"]]
        }, staged_checker=self.check_staged_okf)
        with self.assertRaises(WriterError) as error:
            restricted.write(self.request(
                "move", record_id=source["record_id"],
                expected_version=source["version"],
                destination="openwiki/projects/new.md"))
        self.assertEqual(error.exception.code, "PUBLICATION_DENIED")
        self.assertEqual(git(self.root, "rev-parse", "main"), base)
        self.assertEqual(self.writer.read(backlink["record_id"])["version"],
                         backlink["version"])

    def test_move_only_capability_cannot_modify_backlink(self):
        _, source, backlink = self.seed_linked_move()
        head = git(self.root, "rev-parse", "main")
        # The target itself is movable, but inbound link repair requires
        # explicit permission for the UPDATE operation too.
        move_only = GitRecordWriter(self.root, {
            **self.capability, "operations": ["read", "move"],
        }, staged_checker=self.check_staged_okf)
        with self.assertRaises(WriterError) as denied:
            move_only.write(self.request(
                "move", record_id=source["record_id"],
                expected_version=source["version"],
                destination="openwiki/projects/denied.md"))
        self.assertEqual(denied.exception.code, "PUBLICATION_DENIED")
        self.assertEqual(git(self.root, "rev-parse", "main"), head)
        self.assertEqual(self.writer.read(backlink["record_id"])["version"],
                         backlink["version"])

    def test_unsupported_delete_restore_fail_closed(self):
        record = self.create("openwiki/notes/a.md")
        base = git(self.root, "rev-parse", "main")
        for command in ("delete", "restore"):
            with self.subTest(command=command), self.assertRaises(WriterError) as denied:
                self.writer.write(self.request(
                    command, record_id=record["record_id"],
                    expected_version=record["version"]))
            self.assertEqual(denied.exception.code, "VALIDATION_ERROR")
        self.assertEqual(git(self.root, "rev-parse", "main"), base)

    def test_move_noop_collision_broken_fragment_and_invalid_path(self):
        _, source, _ = self.seed_linked_move()
        base = git(self.root, "rev-parse", "main")
        for destination, expected in [
            ("openwiki/notes/a/target.md", "NO_CHANGE"),
            ("openwiki/concepts/topic.md", "VALIDATION_ERROR"),
            ("openwiki/notes/../unsafe.md", "VALIDATION_ERROR"),
        ]:
            with self.subTest(destination=destination):
                with self.assertRaises(WriterError) as error:
                    self.writer.write(self.request(
                        "move", record_id=source["record_id"],
                        expected_version=source["version"],
                        destination=destination))
                self.assertEqual(error.exception.code, expected)
                self.assertEqual(git(self.root, "rev-parse", "main"), base)

    def test_alias_ambiguity_after_old_path_reuse(self):
        first = self.create("openwiki/notes/first.md")
        request = self.request(
            "move", record_id=first["record_id"],
            expected_version=first["version"],
            destination="openwiki/ideas/moved.md")
        self.writer.write(request)
        second = self.create("openwiki/notes/first.md", title="Reused")
        logs = self.writer._logs(git(self.root, "rev-parse", "main"))
        current = {
            "openwiki/notes/first.md": (second["record_id"], "Reused"),
            "openwiki/ideas/moved.md": (first["record_id"], "Record"),
        }
        resolved = resolve_historical_path("openwiki/notes/first.md",
                                           logs, current)
        self.assertEqual(resolved["kind"], "ambiguous")
        self.assertEqual({x["record_id"] for x in resolved["choices"]},
                         {first["record_id"], second["record_id"]})


if __name__ == "__main__":
    unittest.main()
