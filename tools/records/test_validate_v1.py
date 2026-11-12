"""Real disposable-Git acceptance fixtures for v1 record/event integrity."""
import copy
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

SCRIPT = Path(__file__).with_name("validate_v1.py")
spec = importlib.util.spec_from_file_location("v1_integrity", SCRIPT)
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)


def new_id():
    return str(uuid.uuid4())


class ValidatorFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.record_id = new_id()
        self.event_id = new_id()
        self.path = "openwiki/notes/example.md"
        self.record = self.source(self.record_id)
        self.event = self.make_event(self.record)
        self.install()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def source(self, record_id, extra="", body="Body"):
        return ('---\nid: "' + record_id + '"\nschema_version: 1\n'
                'type: note\ntitle: Example\nstatus: draft\nvisibility: private\n'
                + extra + '---\n\n' + body + '\n')

    def make_event(self, after, **changes):
        event = {
            "schema_version": 1,
            "id": new_id(),
            "record_id": self.record_id,
            "operation_id": new_id(),
            "sequence": 1,
            "action": "CREATED",
            "recorded_at": "2026-11-12T08:00:00Z",
            "occurred_on": None,
            "occurred_at": None,
            "actor": {"id": "test-agent", "kind": "agent", "label": "Fixture Agent"},
            "summary": "Create the example record",
            "path_before": None,
            "path_after": self.path,
            "before": None,
            "after": after,
            "before_sha256": None,
            "after_sha256": v1.digest(after),
            "previous_event_id": None,
            "idempotency_key": new_id(),
            "request_sha256": "a"*64,
            "provenance": {"kind": "native", "source_ref": None, "original_time": None},
        }
        event.update(changes)
        return event

    def write(self, path, data):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(data, encoding="utf-8")

    def install(self, events=None):
        shutil.rmtree(self.root / 'openwiki', ignore_errors=True)
        events = [self.event] if events is None else events
        self.write(self.path, events[-1]["after"])
        log = "# Record history\n\n" + "\n".join(
            "## Entry " + e["id"] + "\n" + chr(96)*3 + "json\n" +
            json.dumps(e, ensure_ascii=False, indent=2) + "\n" + chr(96)*3 + "\n"
            for e in events)
        self.write(self.path[:-3] + ".log.md", log)
        self.write("openwiki/index.md",
                   '---\nokf_version: "0.2"\n---\n\n# Root\n\n* [Notes](notes/)\n')
        self.write("openwiki/notes/index.md", "# Notes\n\n* [Example](example.md)\n")
        self.git("add", "-A")

    def check(self, base=None, strict=False):
        return v1.repository(self.root, base=base, strict_indexes=strict)

    def assert_invalid(self, needle=None, base=None):
        with self.assertRaises(v1.IntegrityError) as context:
            self.check(base=base)
        if needle:
            self.assertIn(needle, str(context.exception))

    def test_valid_native_fixture_and_exact_indexes(self):
        self.assertEqual(self.check(strict=True), {"records": 1, "events": 1})

    def test_valid_depth_eight_hierarchy(self):
        self.path = "openwiki/notes/a/b/c/d/e/f/g/example.md"
        self.event["path_after"] = self.path
        self.install()
        folder = Path(self.path).parent
        # Regenerate all eight structural indexes and their direct child entries.
        self.write("openwiki/index.md",
                   '---\nokf_version: "0.2"\n---\n\n# Root\n\n* [Notes](notes/)\n')
        for depth in range(1, 9):
            current = Path(*folder.parts[:depth+1])
            child = folder.parts[depth+1] + "/" if depth < 8 else "example.md"
            self.write(str(current / "index.md"),
                       "# Index\n\n* [Item](" + child + ")\n")
        self.git("add", "-A")
        self.assertEqual(self.check(strict=True)["records"], 1)

    def test_duplicate_yaml_key_and_alias_rejected(self):
        self.record = self.record.replace("title: Example", "title: One\ntitle: Two")
        self.event = self.make_event(self.record)
        self.install()
        self.assert_invalid("duplicate key")
        self.record = self.source(self.record_id, extra="tags: &some [a]\nx_safe: *some\n")
        self.event = self.make_event(self.record)
        self.install()
        self.assert_invalid("aliases")

    def test_reminder_dates_offsets_and_invalid_occurrence(self):
        self.record = self.source(
            self.record_id, extra='occurred_on: "2026-11-12"\n'
            'occurred_at: "2026-11-12T12:00:00+01:00"\n'
            'reminders:\n  - [["2026-12-01", "2026-12-08"], "Review"]\n'
            '  - [["2026-12-10T08:00:00+01:00", "2026-12-10T09:00:00+01:00"], "Meet"]\n')
        self.event = self.make_event(self.record)
        self.install()
        self.check()
        self.record = self.record.replace("2026-11-12T12:00:00+01:00",
                                          "2026-11-12T12:00:00")
        self.event = self.make_event(self.record)
        self.install()
        self.assert_invalid("offset-qualified")

    def test_duplicate_json_keys_and_stray_text_rejected(self):
        p = self.root / (self.path[:-3] + ".log.md")
        text = p.read_text()
        p.write_text(text.replace('"sequence": 1,', '"sequence": 1,\n  "sequence": 1,'))
        self.git("add", "-A")
        self.assert_invalid("duplicate JSON key")
        self.install()
        p.write_text(p.read_text() + "unmatched text\n")
        self.git("add", "-A")
        self.assert_invalid("expected blank line between events")

    def test_hash_sequence_previous_and_chain_fail(self):
        bad = copy.deepcopy(self.event)
        bad["after_sha256"] = "0"*64
        self.install([bad])
        self.assert_invalid("after hash mismatch")
        bad = copy.deepcopy(self.event)
        bad["sequence"] = 2
        self.install([bad])
        self.assert_invalid("broken sequence")
        bad = copy.deepcopy(self.event)
        bad["previous_event_id"] = new_id()
        self.install([bad])
        self.assert_invalid("first event")
        bad = copy.deepcopy(self.event)
        bad["record_id"] = new_id()
        self.install([bad])
        self.assert_invalid("wrong record ID")

    def test_duplicate_ids_and_missing_or_orphan_log(self):
        twin = "openwiki/ideas/example.md"
        self.write(twin, self.record)
        self.write(twin[:-3] + ".log.md",
                   (self.root / (self.path[:-3]+".log.md")).read_text()
                   .replace(self.path, twin))
        self.git("add", "-A")
        self.assert_invalid("duplicate global record ID")
        (self.root / twin).unlink()
        self.git("add", "-A")
        self.assert_invalid("orphan v1")
        (self.root / (twin[:-3]+".log.md")).unlink()
        (self.root / (self.path[:-3]+".log.md")).unlink()
        self.git("add", "-A")
        self.assert_invalid("missing sibling log")

    def test_path_limits_symlink_collision_and_size(self):
        self.path = "openwiki/notes/Example.md"
        self.event["path_after"] = self.path
        self.install()
        self.assert_invalid("reserved or invalid slug")
        self.path = "openwiki/notes/example.md"
        self.event["path_after"] = self.path
        self.install()
        self.write("openwiki/notes/EXAMPLE.md", "anything")
        self.git("add", "-A")
        self.assert_invalid("case-insensitive path collision")
        (self.root / "openwiki/notes/EXAMPLE.md").unlink()
        self.git("add", "-A")
        link = self.root / "openwiki/notes/link.md"
        link.symlink_to("example.md")
        self.git("add", "-A")
        self.assert_invalid("symlink at a path component")
        link.unlink()
        self.git("add", "-A")
        self.record = self.source(self.record_id, body="x"*1048576)
        self.event = self.make_event(self.record)
        self.install()
        self.assert_invalid("exceeds 1 MiB")

    def test_trusted_base_rejects_history_rewrite(self):
        self.git("commit", "-qm", "baseline")
        base = self.git("rev-parse", "HEAD")
        self.assertEqual(self.check(base=base)["events"], 1)
        self.event["summary"] = "Retroactively altered history"
        self.install()
        self.assert_invalid("history prefix rewritten", base)

    def test_direct_record_edit_without_event_rejected(self):
        self.git("commit", "-qm", "baseline")
        base = self.git("rev-parse", "HEAD")
        self.write(self.path, self.record.replace("Body\n", "Edited without event\n"))
        self.git("add", "-A")
        self.assert_invalid("final log snapshot", base)

    def test_valid_append_after_committed_base(self):
        self.git("commit", "-qm", "baseline")
        base = self.git("rev-parse", "HEAD")
        final = self.source(self.record_id, body="Revised")
        next_event = self.make_event(final, sequence=2, action="UPDATED",
                                     previous_event_id=self.event["id"],
                                     before=self.record,
                                     before_sha256=v1.digest(self.record),
                                     path_before=self.path,
                                     recorded_at="2026-11-12T08:00:00Z")
        self.install([self.event, next_event])
        self.assertEqual(self.check(base=base)["events"], 2)

    def test_new_non_v1_record_rejected_against_base(self):
        self.git("commit", "-qm", "baseline")
        base = self.git("rev-parse", "HEAD")
        self.write("openwiki/notes/invalid-new.md", "---\ntitle: Old\n---\n")
        self.git("add", "-A")
        self.assert_invalid("new record must use v1", base)


    def test_portable_path_reserved_traversal_and_byte_limit(self):
        for candidate in (
            "openwiki/notes/../escaped.md",
            "openwiki/notes/./hidden.md",
            "openwiki/notes/con.md",
            "openwiki/notes/prn/item.md",
            "openwiki/notes/" + "a"*230 + ".md",
        ):
            with self.subTest(candidate=candidate):
                with self.assertRaises(v1.IntegrityError):
                    v1.safe_path(candidate, "candidate")

    def test_duplicate_event_ids_across_distinct_records(self):
        twin = "openwiki/ideas/second.md"
        second_id = new_id()
        second_source = self.source(second_id)
        second_event = self.make_event(second_source, record_id=second_id,
                                       path_after=twin, id=self.event["id"])
        self.write(twin, second_source)
        self.write(twin[:-3] + ".log.md",
                   "# Record history\n\n## Entry " + second_event["id"] + "\n" +
                   chr(96)*3 + "json\n" +
                   json.dumps(second_event, ensure_ascii=False, indent=2) +
                   "\n" + chr(96)*3 + "\n")
        self.write("openwiki/index.md",
                   '---\nokf_version: "0.2"\n---\n\n# Root\n\n* [Ideas](ideas/)\n* [Notes](notes/)\n')
        self.write("openwiki/ideas/index.md", "# Ideas\n\n* [Second](second.md)\n")
        self.git("add", "-A")
        self.assert_invalid("globally duplicated event ID")

    def test_wrong_sibling_path_and_recorded_timestamp(self):
        wrong = copy.deepcopy(self.event)
        wrong["path_after"] = "openwiki/notes/not-example.md"
        self.install([wrong])
        self.assert_invalid("final log snapshot/path")
        wrong = copy.deepcopy(self.event)
        wrong["recorded_at"] = "2026-11-12T08:00:00+02:00"
        self.install([wrong])
        self.assert_invalid("UTC second-precision Z")

if __name__ == "__main__":
    unittest.main()
