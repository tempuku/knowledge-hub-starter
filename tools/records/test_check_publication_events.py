"""Real disposable-Git tests for the #126 publication event allowlist check."""
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

SCRIPT = Path(__file__).with_name("check_publication_events.py")
POLICY = "config/publication.json"


class PublicationEventFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.record_id = str(uuid.uuid4())
        self.first = str(uuid.uuid4())
        self.second = str(uuid.uuid4())
        self.third = str(uuid.uuid4())
        self.fourth = str(uuid.uuid4())
        self.path = "openwiki/projects/example.md"
        self.log_path = self.path[:-3] + ".log.md"

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def write(self, path, data):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(data, encoding="utf-8")

    def record(self, visibility="public"):
        return ('---\nid: "' + self.record_id + '"\nschema_version: 1\n'
                'type: note\ntitle: "Example"\nstatus: draft\n'
                'visibility: ' + visibility + '\n---\n\nBody\n')

    def log(self, event_ids):
        sections = []
        for sequence, event_id in enumerate(event_ids, 1):
            event = {"schema_version": 1, "id": event_id,
                     "record_id": self.record_id, "sequence": sequence}
            sections.append("## Entry " + event_id + "\n```json\n" +
                            json.dumps(event, ensure_ascii=False, indent=2) +
                            "\n```\n")
        return "# Record history\n\n" + "\n".join(sections)

    def policy(self, record_ids=(), event_ids=()):
        payload = {"schema_version": 1, "record_ids": sorted(set(record_ids)),
                   "event_ids": sorted(set(event_ids)),
                   "actor_labels": ["Fixture Agent"]}
        self.write(POLICY, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    def commit(self, message="fixture"):
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def base_commit(self, visibility="public", record_ids=None, event_ids=None,
                    events=None):
        self.write(self.path, self.record(visibility))
        self.write(self.log_path, self.log([self.first] if events is None else events))
        self.policy([self.record_id] if record_ids is None else record_ids,
                    [self.first] if event_ids is None else event_ids)
        return self.commit("base")

    def check(self, base):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), "--base", base],
            cwd=self.root, text=True, capture_output=True)

    def assert_passes(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("publication events: OK:", result.stdout)

    def assert_fails(self, result, *needles):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for needle in needles:
            self.assertIn(needle, result.stderr)

    def test_new_event_on_allowlisted_public_record_must_be_allowlisted(self):
        base = self.base_commit()
        self.write(self.log_path, self.log([self.first, self.second]))
        self.commit("append event without allowlist update")
        result = self.check(base)
        self.assert_fails(result, self.log_path, "sequence 2", self.second)

    def test_new_event_allowlisted_passes(self):
        base = self.base_commit()
        self.write(self.log_path, self.log([self.first, self.second]))
        self.commit("append event")
        self.policy([self.record_id], [self.first, self.second])
        self.commit("allowlist the new event")
        self.assert_passes(self.check(base))

    def test_non_allowlisted_public_record_is_ignored(self):
        base = self.base_commit(record_ids=(), event_ids=())
        self.write(self.log_path, self.log([self.first, self.second]))
        self.commit("append event to an unapproved record")
        self.assert_passes(self.check(base))

    def test_private_record_is_ignored(self):
        base = self.base_commit(visibility="private")
        self.write(self.log_path, self.log([self.first, self.second]))
        self.commit("append event to a private record")
        self.assert_passes(self.check(base))

    def test_historical_unallowlisted_events_in_base_stay_passing(self):
        base = self.base_commit(events=[self.first, self.second],
                                event_ids=[self.first])
        self.write(self.log_path, self.log([self.first, self.second, self.third]))
        self.commit("append an allowlisted event")
        self.policy([self.record_id], [self.first, self.third])
        self.commit("allowlist only the new event")
        self.assert_passes(self.check(base))

        trusted = self.git("rev-parse", "HEAD")
        self.write(self.log_path,
                   self.log([self.first, self.second, self.third, self.fourth]))
        self.commit("append an unallowlisted event")
        result = self.check(trusted)
        self.assert_fails(result, self.log_path, "sequence 4", self.fourth)
        self.assertNotIn(self.second, result.stderr)

    def test_new_log_on_allowlisted_public_record_fails(self):
        self.write(self.path, self.record())
        self.policy([self.record_id])
        base = self.commit("record without history")
        self.write(self.log_path, self.log([self.first]))
        self.commit("add history without allowlist update")
        result = self.check(base)
        self.assert_fails(result, self.log_path, "sequence 1", self.first)

    def test_legacy_log_is_skipped(self):
        self.write(self.path, self.record())
        self.policy([self.record_id])
        base = self.commit("record without v1 history")
        self.write(self.log_path, "# OKF Record Change Log\n\n- old entry\n")
        self.commit("add legacy log input")
        self.assert_passes(self.check(base))

    def test_deleted_record_does_not_crash(self):
        base = self.base_commit()
        self.write(self.log_path, self.log([self.first, self.second]))
        (self.root / self.path).unlink()
        self.commit("append event and delete record")
        self.assert_passes(self.check(base))

    def test_unparseable_current_log_is_skipped(self):
        base = self.base_commit()
        self.write(self.log_path, "# Record history\n\nnot a section\n")
        self.commit("corrupt log")
        result = self.check(base)
        self.assert_passes(result)
        self.assertIn("cannot read current history", result.stderr)

    def test_missing_allowlist_fails_closed(self):
        base = self.base_commit()
        (self.root / POLICY).unlink()
        self.commit("remove allowlist")
        result = self.check(base)
        self.assert_fails(result, POLICY)

    def test_malformed_allowlist_fails_closed(self):
        base = self.base_commit()
        self.write(POLICY, "{not json\n")
        self.commit("corrupt allowlist")
        result = self.check(base)
        self.assert_fails(result, POLICY, "invalid publication allowlist")


if __name__ == "__main__":
    unittest.main()
