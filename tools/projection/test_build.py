"""Publication safety tests for the opt-in projection entrypoint."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build import publish
from deterministic import ProjectionError
import json
import subprocess
import sys

RECORDS = Path(__file__).resolve().parents[1] / "records"
sys.path.insert(0, str(RECORDS))
import writer_v1 as writer


class PublicationTests(unittest.TestCase):
    def test_public_mode_fails_closed_before_loading_source(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "data"
            with self.assertRaises(ProjectionError):
                publish(Path(directory), destination, "HEAD", mode="public")
            self.assertFalse(destination.exists())

    def test_excluded_record_and_event_references_fail_before_manifest_switch(self):
        # Run a real Git publication separately for each forbidden token so one
        # leaked reference cannot mask another in the byte-audit regression.
        ids = {
            "private_record": "123e4567-e89b-42d3-a456-426614174000",
            "private_event": "123e4567-e89b-42d3-a456-426614174001",
            "private_op": "123e4567-e89b-42d3-a456-426614174002",
            "public_record": "123e4567-e89b-42d3-a456-426614174003",
            "public_event": "123e4567-e89b-42d3-a456-426614174004",
            "public_op": "123e4567-e89b-42d3-a456-426614174005",
            "transition_record": "123e4567-e89b-42d3-a456-426614174006",
            "transition_created": "123e4567-e89b-42d3-a456-426614174007",
            "transition_updated": "123e4567-e89b-42d3-a456-426614174008",
            "transition_create_op": "123e4567-e89b-42d3-a456-426614174009",
            "transition_update_op": "123e4567-e89b-42d3-a456-426614174010",
        }
        for leak in (ids["private_record"], "openwiki/notes/private-note.md", ids["transition_updated"]):
            with self.subTest(leak=leak), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                subprocess.run(["git", "init", "-q"], cwd=root, check=True)
                subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
                subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
                files = {"openwiki/index.md": '---\nokf_version: "0.2"\n---\n\n# Root\n'}
                entries = []
                for name, visibility, body, path in (
                    ("private", "private", "Private source body", "openwiki/notes/private-note.md"),
                    ("public", "public", "Public reference " + leak, "openwiki/notes/public-note.md"),
                ):
                    rid, eid, oid = ids[name+"_record"], ids[name+"_event"], ids[name+"_op"]
                    source = ("---\ntype: note\ntitle: \"" + name.title() + " note\"\nvisibility: " + visibility +
                              "\nstatus: stable\n---\n\n" + body + "\n")
                    after = writer.create_source(source, rid)
                    request = writer.normalized_request({
                        "command": "create", "idempotency_key": oid,
                        "actor": {"id": "fixture-actor-" + name, "kind": "agent", "label": "Contributor"},
                        "summary": "Create fixture record", "expected_head": "a" * 40,
                        "path": path, "content": source,
                    })
                    event = writer.make_event(request, record_id=rid, event_id=eid,
                        operation_id=oid, sequence=1, action="CREATED", path_before=None,
                        path_after=path, before=None, after=after, previous_event_id=None,
                        recorded_at="2026-11-12T08:00:00Z")
                    files[path] = after
                    files[path[:-3] + ".log.md"] = writer.append_log(None, event)
                    entries.append(path)
                # Add an allowlisted public-current record whose only event is a
                # private-before -> public-after transition; the transition ID is
                # not selected and must remain forbidden to the byte audit.
                tr_id = ids["transition_record"]
                tr_path = "openwiki/notes/transition-note.md"
                before_source = "---\ntype: note\ntitle: \"Transition note\"\nvisibility: private\nstatus: stable\n---\n\nPrivate before\n"
                after_source = "---\ntype: note\ntitle: \"Transition note\"\nvisibility: public\nstatus: stable\n---\n\nPublic after\n"
                before = writer.create_source(before_source, tr_id)
                after = writer.create_source(after_source, tr_id)
                common = {"actor": {"id": "123e4567-e89b-42d3-a456-426614174011", "kind": "agent", "label": "Contributor"},
                          "summary": "Transition test", "expected_head": "a" * 40}
                create_req = writer.normalized_request({"command": "create", "idempotency_key": ids["transition_create_op"],
                    "path": tr_path, "content": before_source, **common})
                created = writer.make_event(create_req, record_id=tr_id, event_id=ids["transition_created"],
                    operation_id=ids["transition_create_op"], sequence=1, action="CREATED", path_before=None,
                    path_after=tr_path, before=None, after=before, previous_event_id=None,
                    recorded_at="2026-11-12T07:00:00Z")
                update_req = writer.normalized_request({"command": "update", "idempotency_key": ids["transition_update_op"],
                    "record_id": tr_id, "expected_version": ids["transition_created"], "content": after_source, **common})
                updated = writer.make_event(update_req, record_id=tr_id, event_id=ids["transition_updated"],
                    operation_id=ids["transition_update_op"], sequence=2, action="UPDATED", path_before=tr_path,
                    path_after=tr_path, before=before, after=after, previous_event_id=ids["transition_created"],
                    recorded_at="2026-11-12T08:00:00Z")
                files[tr_path] = after
                files[tr_path[:-3] + ".log.md"] = writer.append_log(writer.append_log(None, created), updated)
                files["openwiki/notes/index.md"] = "# Notes\n"
                policy = {"schema_version": 1,
                          "record_ids": sorted([ids["private_record"], ids["public_record"], tr_id]),
                          "event_ids": sorted([ids["private_event"], ids["public_event"], ids["transition_created"], ids["transition_updated"]]),
                          "actor_labels": ["Contributor"]}
                files["config/publication.json"] = json.dumps(policy, indent=2) + "\n"
                for path, content in files.items():
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                subprocess.run(["git", "add", "-A"], cwd=root, check=True)
                subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
                destination = root / "published"
                destination.mkdir()
                manifest = destination / "manifest.json"
                manifest.write_bytes(b"previous-manifest\n")
                with self.assertRaisesRegex(ProjectionError, "private reference detected"):
                    publish(root, destination, "HEAD", mode="public")
                self.assertEqual(manifest.read_bytes(), b"previous-manifest\n")
                self.assertFalse((destination / "g").exists())

    def test_private_manifest_is_switched_only_after_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "data"
            record = {"id": "r1", "title": "A", "description": "",
                      "type": "note", "status": "draft", "project_id": None,
                      "tags": [], "area": "notes", "updated_at": "2026-11-12T12:00:00Z",
                      "version": 1, "content_bytes": 2, "content": "a\n",
                      "path": "openwiki/notes/a.md"}
            event = {"id": "e1", "record_id": "r1", "sequence": 1,
                     "recorded_at": "2026-11-12T12:00:00Z", "before": None,
                     "after": "a\n", "path_before": None, "path_after": record["path"]}
            summary = {"id": "e1", "record_id": "r1", "sequence": 1,
                       "recorded_at": event["recorded_at"]}
            with patch("build.load_revision", return_value=("c" * 40, "a" * 40,
                    [record], {"r1": [event]}, {"e1": summary})):
                manifest = publish(Path(directory), destination, "HEAD")
                self.assertTrue((destination / "g" / manifest["generation"] / "catalog.json").exists())
                self.assertTrue((destination / "manifest.json").exists())
                with self.assertRaises(ProjectionError):
                    publish(Path(directory), destination, "HEAD")
            self.assertEqual(manifest["mode"], "private")


if __name__ == "__main__":
    unittest.main()
