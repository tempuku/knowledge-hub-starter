"""Real-Git privacy acceptance for public/private projection generations.

The fixture canonical files and logs are emitted by the v1 writer primitives,
committed to a disposable repository, then loaded through the production source
validator and publication entrypoint. It contains no personal data.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "records")]

from build import publish
from deterministic import ProjectionError
from git_source import load_revision
from publication import (audit_public, forbidden_public_references,
                         validate_policy)
import writer_v1 as writer


IDS = {
    "private_record": "10000000-0000-4000-8000-000000000001",
    "private_event": "10000000-0000-4000-8000-000000000002",
    "private_op": "10000000-0000-4000-8000-000000000003",
    "public_record": "20000000-0000-4000-8000-000000000001",
    "public_event": "20000000-0000-4000-8000-000000000002",
    "public_op": "20000000-0000-4000-8000-000000000003",
    "public_move_event": "20000000-0000-4000-8000-000000000004",
    "public_move_op": "20000000-0000-4000-8000-000000000005",
    "transition_record": "30000000-0000-4000-8000-000000000001",
    "transition_create": "30000000-0000-4000-8000-000000000002",
    "transition_create_op": "30000000-0000-4000-8000-000000000003",
    "transition_update": "30000000-0000-4000-8000-000000000004",
    "transition_update_op": "30000000-0000-4000-8000-000000000005",
    "linked_record": "40000000-0000-4000-8000-000000000001",
    "linked_event": "40000000-0000-4000-8000-000000000002",
    "linked_op": "40000000-0000-4000-8000-000000000003",
    "fallback_record": "50000000-0000-4000-8000-000000000001",
    "fallback_event": "50000000-0000-4000-8000-000000000002",
    "fallback_op": "50000000-0000-4000-8000-000000000003",
}


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def source(title: str, visibility: str, body: str, *, extra: str = "") -> str:
    fields = (f'type: note\ntitle: "{title}"\nstatus: stable\n'
              f'visibility: {visibility}\n{extra}')
    return f"---\n{fields}---\n\n{body}\n"


def append_created(root: Path, path: str, rid: str, eid: str, oid: str,
                   input_source: str, after: str, *, timestamp: str,
                   actor_label: str = "Fixture editor"):
    request = writer.normalized_request({
        "command": "create", "idempotency_key": oid,
        "actor": {"id": "fixture-human-private-actor", "kind": "human", "label": actor_label},
        "summary": "Create synthetic acceptance record",
        "expected_head": git(root, "rev-parse", "HEAD"),
        "path": path, "content": input_source,
    })
    event = writer.make_event(request, record_id=rid, event_id=eid,
        operation_id=oid, sequence=1, action="CREATED", path_before=None,
        path_after=path, before=None, after=after, previous_event_id=None,
        recorded_at=timestamp)
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(after, encoding="utf-8", newline="")
    (root / (path[:-3] + ".log.md")).write_text(writer.append_log(None, event), encoding="utf-8", newline="")
    return event


def make_fixture(root: Path):
    git(root, "init", "-q")
    git(root, "config", "user.name", "Acceptance fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    (root / "openwiki").mkdir()
    (root / "openwiki/index.md").write_text('---\nokf_version: "0.2"\n---\n\n# Root\n', encoding="utf-8")
    (root / "openwiki/notes").mkdir()
    (root / "openwiki/notes/index.md").write_text("# Notes index\n", encoding="utf-8")
    git(root, "add", "-A")
    subprocess.run(["git", "commit", "-qm", "fixture baseline"], cwd=root, check=True)

    private_input = source("Private title canary", "private",
        "# Secret Heading\n\nPrivate body canary retained only in private source.",
        extra=('reminders:\n  - ["2027-01-12", "Private reminder canary"]\n'
               'sources:\n  - resource: "https://example.invalid/private-source-canary"\n'
               '    title: "Private source title canary"\n'))
    private_after = writer.create_source(private_input, IDS["private_record"])
    private_event = append_created(root, "openwiki/notes/private-note.md",
        IDS["private_record"], IDS["private_event"], IDS["private_op"],
        private_input, private_after, timestamp="2026-11-12T07:00:00Z")

    public_input = source("Public record", "public", "Public body canary.",
        extra='reminders:\n  - ["2027-01-20", "Public reminder retained"]\n')
    public_after = writer.create_source(public_input, IDS["public_record"])
    public_event = append_created(root, "openwiki/notes/public-note.md",
        IDS["public_record"], IDS["public_event"], IDS["public_op"],
        public_input, public_after, timestamp="2026-11-12T08:00:00Z")
    public_move_req = writer.normalized_request({
        "command": "move", "idempotency_key": IDS["public_move_op"],
        "record_id": IDS["public_record"], "expected_version": IDS["public_event"],
        "actor": {"id": "fixture-human-private-actor", "kind": "human", "label": "Fixture editor"},
        "summary": "Move public fixture", "expected_head": git(root, "rev-parse", "HEAD"),
        "destination": "openwiki/notes/public-note-new.md",
    })
    public_move_event = writer.make_event(public_move_req,
        record_id=IDS["public_record"], event_id=IDS["public_move_event"],
        operation_id=IDS["public_move_op"], sequence=2, action="MOVED",
        path_before="openwiki/notes/public-note.md",
        path_after="openwiki/notes/public-note-new.md", before=public_after,
        after=public_after, previous_event_id=IDS["public_event"],
        recorded_at="2026-11-12T08:30:00Z")
    (root / "openwiki/notes/public-note.md").unlink()
    (root / "openwiki/notes/public-note.log.md").unlink()
    (root / "openwiki/notes/public-note-new.md").write_text(public_after, encoding="utf-8", newline="")
    (root / "openwiki/notes/public-note-new.log.md").write_text(
        writer.append_log(writer.append_log(None, public_event), public_move_event),
        encoding="utf-8", newline="")

    transition_path = "openwiki/notes/transition-note.md"
    transition_private_input = source("Transition private title canary", "private",
        "Transition private body canary.",
        extra='reminders:\n  - ["2027-02-03", "Transition private reminder canary"]\n')
    transition_before = writer.create_source(transition_private_input, IDS["transition_record"])
    transition_create_req = writer.normalized_request({
        "command": "create", "idempotency_key": IDS["transition_create_op"],
        "actor": {"id": "transition-private-actor", "kind": "agent", "label": "Fixture editor"},
        "summary": "Create private transition source", "expected_head": git(root, "rev-parse", "HEAD"),
        "path": transition_path, "content": transition_private_input,
    })
    transition_create = writer.make_event(transition_create_req,
        record_id=IDS["transition_record"], event_id=IDS["transition_create"],
        operation_id=IDS["transition_create_op"], sequence=1, action="CREATED",
        path_before=None, path_after=transition_path, before=None,
        after=transition_before, previous_event_id=None,
        recorded_at="2026-11-12T09:00:00Z")
    transition_public_input = source("Transition public title", "public",
        "Transition public body canary.",
        extra='reminders:\n  - ["2027-03-04", "Transition public reminder retained"]\n')
    transition_after = transition_public_input.replace("type: note", f'id: "{IDS["transition_record"]}"\nschema_version: 1\ntype: note')
    # Update input is a full canonical source and is validated by the writer.
    update_req = writer.normalized_request({
        "command": "update", "idempotency_key": IDS["transition_update_op"],
        "record_id": IDS["transition_record"], "expected_version": IDS["transition_create"],
        "actor": {"id": "transition-private-actor", "kind": "agent", "label": "Fixture editor"},
        "summary": "Publish current transition record", "expected_head": git(root, "rev-parse", "HEAD"),
        "content": transition_after, "publish_current": True,
    })
    transition_updated = writer.make_event(update_req,
        record_id=IDS["transition_record"], event_id=IDS["transition_update"],
        operation_id=IDS["transition_update_op"], sequence=2, action="UPDATED",
        path_before=transition_path, path_after=transition_path,
        before=transition_before, after=transition_after,
        previous_event_id=IDS["transition_create"], recorded_at="2026-11-12T10:00:00Z")
    (root / transition_path).write_text(transition_after, encoding="utf-8", newline="")
    (root / "openwiki/notes/transition-note.log.md").write_text(
        writer.append_log(writer.append_log(None, transition_create), transition_updated),
        encoding="utf-8", newline="")

    linked_input = source("Linked public record", "public",
        "See [click](index.md), [click](private-note.md#secret-heading) and "
        "[Public target](public-note-new.md).")
    linked_after = writer.create_source(linked_input, IDS["linked_record"])
    linked_event = append_created(root, "openwiki/notes/linked-note.md",
        IDS["linked_record"], IDS["linked_event"], IDS["linked_op"],
        linked_input, linked_after, timestamp="2026-11-12T11:00:00Z")

    fallback_input = source("Fallback public record", "public", "Fallback body.")
    fallback_after = writer.create_source(fallback_input, IDS["fallback_record"])
    fallback_event = append_created(root, "openwiki/notes/fallback-note.md",
        IDS["fallback_record"], IDS["fallback_event"], IDS["fallback_op"],
        fallback_input, fallback_after, timestamp="2026-11-12T12:00:00Z",
        actor_label="Unapproved fixture editor")

    policy = {"schema_version": 1,
              "record_ids": sorted([IDS["private_record"], IDS["public_record"],
                                    IDS["transition_record"], IDS["linked_record"],
                                    IDS["fallback_record"]]),
              "event_ids": sorted([IDS["private_event"], IDS["public_event"],
                                   IDS["transition_create"], IDS["transition_update"],
                                   IDS["fallback_event"], IDS["public_move_event"]]),
              "actor_labels": ["Fixture editor"]}
    (root / "config").mkdir()
    (root / "config/publication.json").write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    git(root, "add", "-A")
    subprocess.run(["git", "commit", "-qm", "writer generated records and logs"], cwd=root, check=True)
    return policy, [private_event, public_event, public_move_event, transition_create, transition_updated,
                    linked_event, fallback_event]


class PrivacyAcceptanceTests(unittest.TestCase):
    def test_real_git_public_and_private_generations_have_independent_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            policy, events = make_fixture(root)
            revision = git(root, "rev-parse", "HEAD")
            # This is a real immutable Git build and full source-chain validation.
            commit, _, source_records, source_histories, summaries = load_revision(root, revision)
            self.assertEqual(commit, revision)
            self.assertEqual(len(source_records), 5)
            self.assertEqual(sum(map(len, source_histories.values())), 7)
            self.assertEqual(set(e["id"] for e in events),
                             {e["id"] for h in source_histories.values() for e in h})

            public_dir, private_dir = Path(temp) / "public", Path(temp) / "private"
            public_manifest = publish(root, public_dir, revision, mode="public")
            private_manifest = publish(root, private_dir, revision, mode="private")
            self.assertEqual(public_manifest["mode"], "public")
            self.assertEqual(private_manifest["mode"], "private")
            self.assertNotEqual(public_manifest["generation"], private_manifest["generation"])
            self.assertNotEqual(public_manifest["policy_digest"], private_manifest["policy_digest"])

            public_generation = public_dir / "g" / public_manifest["generation"]
            private_generation = private_dir / "g" / private_manifest["generation"]
            public_files = {path.relative_to(public_generation).as_posix(): path.read_bytes()
                            for path in public_generation.rglob("*.json")}
            private_files = {path.relative_to(private_generation).as_posix(): path.read_bytes()
                             for path in private_generation.rglob("*.json")}
            public_outputs = {**public_files, "manifest.json": (public_dir / "manifest.json").read_bytes()}
            private_outputs = {**private_files, "manifest.json": (private_dir / "manifest.json").read_bytes()}
            private_inventory = {path: hashlib.sha256(data).hexdigest()
                                 for path, data in sorted(private_outputs.items())}
            self.assertEqual(set(private_inventory), set(private_outputs))
            self.assertEqual(len(private_inventory), len(private_outputs))
            self.assertEqual(private_manifest["policy_digest"], "private-v1")
            public_records = {json.loads(public_files[f"records/{rid}.json"])["id"]
                              for rid in (IDS["public_record"], IDS["transition_record"],
                                          IDS["linked_record"], IDS["fallback_record"])}
            self.assertEqual(public_records,
                             {IDS["public_record"], IDS["transition_record"],
                              IDS["linked_record"], IDS["fallback_record"]})
            self.assertNotIn(f"records/{IDS['private_record']}.json", public_files)
            public_catalog = json.loads(public_files["catalog.json"])
            private_catalog = json.loads(private_files["catalog.json"])
            self.assertEqual((public_catalog["record_count"], public_catalog["event_count"]), (4, 3))
            self.assertEqual((private_catalog["record_count"], private_catalog["event_count"]), (5, 7))

            # Verify current hidden link handling and actor/operation redaction.
            linked = json.loads(public_files[f"records/{IDS['linked_record']}.json"])
            self.assertNotIn(IDS["private_record"], linked["content"])
            self.assertNotIn("Private title canary", linked["content"])
            self.assertNotIn("private-note.md", linked["content"])
            self.assertIn("[click](index.md)", linked["content"])
            self.assertIn(f"record:{IDS['public_record']}", linked["content"])
            self.assertEqual(linked["links"], [
                {"target_id": None, "fragment": None,
                 "label": "Unavailable in this view", "available": False, "href": None},
                {"target_id": IDS["public_record"], "fragment": None,
                 "label": "Public target", "available": True,
                 "href": f"record:{IDS['public_record']}"},
            ])

            # Reverse links are generated from authorization-scoped current edges.
            # Private targets exist only in the authenticated private graph.
            public_target = json.loads(public_files[f"records/{IDS['public_record']}.json"])
            private_target = json.loads(private_files[f"records/{IDS['private_record']}.json"])
            expected_backlink = [{"source_id": IDS["linked_record"],
                                  "title": "Linked public record"}]
            self.assertEqual(public_target["backlinks"], expected_backlink)
            self.assertEqual(private_target["backlinks"], expected_backlink)
            self.assertNotIn(f"records/{IDS['private_record']}.json", public_files)
            self.assertEqual(linked["content_bytes"], len(linked["content"].encode("utf-8")))
            published_event = json.loads(public_files[f"events/{IDS['public_event']}.json"])["event"]
            self.assertEqual(published_event["actor"]["id"], "redacted")
            self.assertEqual(published_event["actor"]["label"], "Fixture editor")
            self.assertEqual(published_event["operation_id"], "redacted")
            self.assertEqual(published_event["idempotency_key"], "redacted")
            self.assertEqual(published_event["request_sha256"], "redacted")
            self.assertIsNone(published_event["provenance"]["source_ref"])
            self.assertIsNone(published_event["provenance"]["original_time"])
            fallback_event = json.loads(public_files[f"events/{IDS['fallback_event']}.json"])["event"]
            self.assertEqual(fallback_event["actor"]["label"], "Contributor")
            self.assertEqual(json.loads(public_files["history/" + IDS["transition_record"] + "/index.json"])["event_count"], 0)
            self.assertEqual(json.loads(public_files["history/" + IDS["public_record"] + "/index.json"])["event_count"], 2)
            public_reminders = [item for path, content in public_files.items()
                                if path.startswith("reminders/")
                                for item in json.loads(content)["items"]]
            self.assertEqual({item["text"] for item in public_reminders},
                             {"Public reminder retained", "Transition public reminder retained"})
            private_reminders = [item for path, content in private_files.items()
                                 if path.startswith("reminders/")
                                 for item in json.loads(content)["items"]]

            # Audit each public generated JSON file and the root manifest bytes.
            public_records_in = source_records
            selected_records = [r for r in source_records
                                if r["id"] in (IDS["public_record"], IDS["transition_record"],
                                               IDS["linked_record"], IDS["fallback_record"])]
            selected_histories = {
                IDS["public_record"]: source_histories[IDS["public_record"]],
                IDS["transition_record"]: [], IDS["linked_record"]: [],
                IDS["fallback_record"]: source_histories[IDS["fallback_record"]],
            }
            forbidden = forbidden_public_references(public_records_in, source_histories,
                                                    selected_records, selected_histories)
            manifest_bytes = public_outputs["manifest.json"]
            all_public_outputs = public_outputs
            audit = audit_public(all_public_outputs, forbidden,
                                 policy_digest=public_manifest["policy_digest"])
            self.assertEqual(audit["count"], len(all_public_outputs))
            self.assertEqual(set(audit["artifacts"]), set(all_public_outputs))
            self.assertEqual(audit["policy_digest"], public_manifest["policy_digest"])
            self.assertEqual(audit["artifacts"]["manifest.json"], hashlib.sha256(manifest_bytes).hexdigest())
            original_aliases = json.loads(public_files["aliases.json"])
            self.assertEqual(original_aliases["paths"]["openwiki/notes/public-note.md"],
                             [IDS["public_record"]])

            # Each private canary must be absent from every public byte, even
            # when it appears in a title, reminder, source URL or event snapshot.
            combined = b"\n".join(all_public_outputs.values())
            for secret in (
                IDS["private_record"], IDS["private_event"], IDS["transition_create"],
                IDS["transition_update"], IDS["linked_event"],
                "openwiki/notes/private-note.md",
                "Private title canary", "Private body canary retained only in private source.",
                "Private reminder canary", "https://example.invalid/private-source-canary",
                "Private source title canary", "Transition private title canary",
                "Transition private body canary.", "Transition private reminder canary",
                "fixture-human-private-actor", "transition-private-actor",
                "Unapproved fixture editor",
            ):
                self.assertNotIn(secret.encode(), combined)
            combined_private = b"\n".join(private_outputs.values())
            self.assertIn("Private body canary retained only in private source.".encode(), combined_private)
            self.assertIn(IDS["private_record"].encode(), combined_private)

            # If an otherwise public event snapshot still names a known
            # private target, allowlisting the event must fail the real build.
            policy["event_ids"].append(IDS["linked_event"])
            policy["event_ids"].sort()
            (root / "config/publication.json").write_text(json.dumps(policy, indent=2) + "\n",
                                                          encoding="utf-8")
            git(root, "add", "config/publication.json")
            subprocess.run(["git", "commit", "-qm", "try unsafe public event"], cwd=root, check=True)
            unsafe_revision = git(root, "rev-parse", "HEAD")
            unsafe_dir = Path(temp) / "unsafe-public"
            with self.assertRaises(ProjectionError):
                publish(root, unsafe_dir, unsafe_revision, mode="public")
            self.assertFalse(unsafe_dir.exists())

            # A committed allowlist revocation creates a new generation with
            # the record, event, reminder, alias target and all counts removed.
            policy["record_ids"].remove(IDS["public_record"])
            policy["record_ids"].remove(IDS["fallback_record"])
            policy["event_ids"].remove(IDS["public_event"])
            policy["event_ids"].remove(IDS["public_move_event"])
            policy["event_ids"].remove(IDS["fallback_event"])
            policy["event_ids"].remove(IDS["linked_event"])
            (root / "config/publication.json").write_text(json.dumps(policy, indent=2) + "\n",
                                                          encoding="utf-8")
            git(root, "add", "config/publication.json")
            subprocess.run(["git", "commit", "-qm", "revoke public records"], cwd=root, check=True)
            revoked_revision = git(root, "rev-parse", "HEAD")
            revoked_manifest = publish(root, public_dir, revoked_revision, mode="public")
            self.assertNotEqual(public_manifest["generation"], revoked_manifest["generation"])
            revoked_generation = public_dir / "g" / revoked_manifest["generation"]
            revoked_files = {path.relative_to(revoked_generation).as_posix(): path.read_bytes()
                             for path in revoked_generation.rglob("*.json")}
            revoked_catalog = json.loads(revoked_files["catalog.json"])
            self.assertEqual((revoked_catalog["record_count"], revoked_catalog["event_count"]), (2, 0))
            self.assertNotIn(f"records/{IDS['public_record']}.json", revoked_files)
            self.assertNotIn(f"events/{IDS['public_event']}.json", revoked_files)
            revoked_bytes = b"\n".join(revoked_files.values())
            for secret in (IDS["public_record"], IDS["public_event"], IDS["public_move_event"],
                           "openwiki/notes/public-note.md", "Public body canary"):
                self.assertNotIn(secret.encode(), revoked_bytes)
            revoked_aliases = json.loads(revoked_files["aliases.json"])
            self.assertNotIn(IDS["public_record"],
                             {rid for ids in revoked_aliases["paths"].values() for rid in ids})
            self.assertNotIn("openwiki/notes/public-note.md", revoked_aliases["paths"])
            self.assertNotIn(IDS["public_event"], set(revoked_aliases["entries"].values()))
            revoked_reminders = [item for path, content in revoked_files.items()
                                 if path.startswith("reminders/")
                                 for item in json.loads(content)["items"]]
            self.assertEqual([item["text"] for item in revoked_reminders],
                             ["Transition public reminder retained"])

            # Optional CI artifact: only fixture/revision hashes, counts,
            # policy digests, and per-file hashes; never source bodies.
            revoked_outputs = {**revoked_files,
                              "manifest.json": (public_dir / "manifest.json").read_bytes()}
            revoked_inventory = {path: hashlib.sha256(data).hexdigest()
                                 for path, data in sorted(revoked_outputs.items())}
            observed = {
                "public": {"records": public_catalog["record_count"],
                           "events": public_catalog["event_count"],
                           "reminders": len(public_reminders),
                           "path_aliases": len(original_aliases["paths"]),
                           "event_aliases": len(original_aliases["entries"])},
                "private": {"records": private_catalog["record_count"],
                            "events": private_catalog["event_count"],
                            "reminders": len(private_reminders),
                            "path_aliases": len(json.loads(private_files["aliases.json"])["paths"]),
                            "event_aliases": len(json.loads(private_files["aliases.json"])["entries"])},
                "revoked_public": {"records": revoked_catalog["record_count"],
                                   "events": revoked_catalog["event_count"],
                                   "reminders": len(revoked_reminders),
                                   "path_aliases": len(revoked_aliases["paths"]),
                                   "event_aliases": len(revoked_aliases["entries"])},
            }
            expected = {
                "public": {"records": 4, "events": 3, "reminders": 2,
                           "path_aliases": 1, "event_aliases": 0},
                "private": {"records": 5, "events": 7, "reminders": 3,
                            "path_aliases": 1, "event_aliases": 0},
                "revoked_public": {"records": 2, "events": 0, "reminders": 1,
                                   "path_aliases": 0, "event_aliases": 0},
            }
            self.assertEqual(observed, expected)

            def generation_paths(inventory, generation):
                return {("manifest.json" if path == "manifest.json"
                         else f"g/{generation}/{path}"): digest
                        for path, digest in inventory.items()}

            artifact_inventory = {
                "public": generation_paths(audit["artifacts"], public_manifest["generation"]),
                "private": generation_paths(private_inventory, private_manifest["generation"]),
                "revoked_public": generation_paths(revoked_inventory, revoked_manifest["generation"]),
            }
            self.assertEqual(set(artifact_inventory["public"]),
                {"manifest.json", *{f"g/{public_manifest['generation']}/{path}" for path in public_files}})
            self.assertEqual(set(artifact_inventory["private"]),
                {"manifest.json", *{f"g/{private_manifest['generation']}/{path}" for path in private_files}})
            self.assertEqual(set(artifact_inventory["revoked_public"]),
                {"manifest.json", *{f"g/{revoked_manifest['generation']}/{path}" for path in revoked_files}})
            report = {
                "schema_version": 1,
                "fixture_revision": revision,
                "fixture_tree_sha256": git(root, "rev-parse", f"{revision}^{{tree}}"),
                "generations": {
                    "public": public_manifest["generation"],
                    "private": private_manifest["generation"],
                    "revoked_public": revoked_manifest["generation"],
                },
                "expected_counts": expected,
                "observed_counts": observed,
                "policy_digests": {
                    "public": public_manifest["policy_digest"],
                    "private": private_manifest["policy_digest"],
                    "revoked_public": revoked_manifest["policy_digest"],
                },
                "artifact_sha256": artifact_inventory,
            }
            report_dir = os.environ.get("KH_ACCEPTANCE_REPORT_DIR")
            if report_dir:
                destination = Path(report_dir)
                destination.mkdir(parents=True, exist_ok=True)
                (destination / "privacy-builds.json").write_text(
                    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_missing_unknown_mode_and_missing_policy_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            make_fixture(root)
            destination = Path(temp) / "out"
            with self.assertRaises(ProjectionError):
                publish(root, destination, "HEAD", mode="unknown")
            self.assertFalse(destination.exists())
            # A committed source revision without the policy is rejected; the
            # dirty working-tree policy from the fixture is never substituted.
            subprocess.run(["git", "rm", "config/publication.json"], cwd=root, check=True,
                           capture_output=True)
            subprocess.run(["git", "commit", "-qm", "remove policy"], cwd=root, check=True)
            with self.assertRaises(ProjectionError):
                publish(root, destination, "HEAD", mode="public")
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
