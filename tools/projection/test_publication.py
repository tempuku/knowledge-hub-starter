"""Regression tests for #32 policy input boundary."""
import json
import unittest
from pathlib import Path

from deterministic import ProjectionError
from publication import (load_policy, validate_policy, select_public, audit_public,
                         forbidden_public_references, _rewrite_markdown_links,
                         _add_private_snapshot)

RID = "123e4567-e89b-42d3-a456-426614174000"
EID = "123e4567-e89b-42d3-a456-426614174001"


class PolicyTests(unittest.TestCase):
    def valid(self):
        return {"schema_version": 1, "record_ids": [RID], "event_ids": [EID],
                "actor_labels": ["Contributor"]}

    def test_valid_policy_digest_is_stable(self):
        policy = self.valid()
        self.assertEqual(validate_policy(json.dumps(policy).encode())[1],
                         validate_policy(json.dumps(policy, indent=2).encode())[1])

    def test_missing_immutable_policy_fails_closed(self):
        with self.assertRaises(ProjectionError):
            load_policy(Path("."), "public")
        with self.assertRaises(ProjectionError):
            load_policy(Path("."), "private", revision_bytes=b"{}")

    def test_reject_invalid_policies(self):
        variants = []
        p = self.valid(); p["record_ids"] = ["*"]; variants.append(p)
        p = self.valid(); p["event_ids"] *= 2; variants.append(p)
        p = self.valid(); p["actor_labels"] = ["z", "a"]; variants.append(p)
        p = self.valid(); p["unexpected"] = 1; variants.append(p)
        p = self.valid(); del p["event_ids"]; variants.append(p)
        p = self.valid(); p["schema_version"] = True; variants.append(p)
        p = self.valid(); p["record_ids"] = ["not-a-uuid"]; variants.append(p)
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ProjectionError):
                validate_policy(json.dumps(variant).encode())

    def test_private_before_public_after_never_exported(self):
        def snap(visibility):
            return "---\nschema_version: 1\nvisibility: " + visibility + "\n---\nbody\n"
        rid = RID
        event = {"id": EID, "record_id": rid, "before": snap("private"),
                 "after": snap("public"), "actor": {"id": "secret-actor",
                 "kind": "agent", "label": "Unapproved"}, "provenance":
                 {"kind": "native", "source_ref": None, "original_time": None}}
        record = {"id": rid, "content": snap("public")}
        records, histories, summaries = select_public([record], {rid: [event]},
            {EID: {"id": EID, "record_id": rid}}, self.valid())
        self.assertEqual(len(records), 1)
        self.assertEqual(histories[rid], [])
        self.assertEqual(summaries, {})

    def test_revocation_excludes_current_and_history(self):
        policy = self.valid()
        policy["record_ids"] = []
        record = {"id": RID, "content": "---\nvisibility: public\n---\nbody\n"}
        records, histories, summaries = select_public([record], {RID: []}, {}, policy)
        self.assertEqual((records, histories, summaries), ([], {}, {}))

    def test_public_byte_audit_detects_ids_and_paths(self):
        for leak in ('private-id', 'openwiki/notes/secret.md'):
            with self.assertRaises(ProjectionError):
                audit_public({"catalog.json": json.dumps({"x": leak}).encode()}, {leak})

    def test_public_artifact_path_is_audited(self):
        with self.assertRaises(ProjectionError):
            audit_public({f"records/{RID}.json": b"{}"}, {RID})

    def test_malformed_private_snapshot_audit_fails_closed(self):
        record = {"id": RID, "path": "openwiki/secret.md", "content": "not frontmatter"}
        with self.assertRaises(ProjectionError):
            forbidden_public_references([record], {RID: []}, [], {})

    def test_legacy_prefrontmatter_history_is_still_forbidden(self):
        excluded = "# Legacy note without YAML\nUnique archived prose\n"
        forbidden = set()
        _add_private_snapshot(forbidden, excluded, legacy_history=True)
        self.assertIn(excluded, forbidden)
        self.assertIn("Unique archived prose", forbidden)
        with self.assertRaises(ProjectionError):
            _add_private_snapshot(set(), "---\ninvalid: [\n---\ncontent\n",
                                  legacy_history=True)
        with self.assertRaises(ProjectionError):
            _add_private_snapshot(set(), excluded)

    def test_filtered_alias_targets_and_keys_are_forbidden(self):
        aliases = {"paths": {"openwiki/old-secret.md": [RID]},
                   "entries": {"legacy-secret-event": EID}}
        forbidden = forbidden_public_references([], {}, [], {},
            source_aliases=aliases, selected_aliases={"paths": {}, "entries": {}})
        self.assertTrue({"openwiki/old-secret.md", "legacy-secret-event", RID, EID} <= forbidden)

    def test_private_history_does_not_hide_current_public_record_identity(self):
        private = "---\nid: \"" + RID + "\"\nschema_version: 1\nvisibility: private\ntitle: Hidden revision title\n---\nHidden revision body.\n"
        public = private.replace("private", "public").replace("Hidden revision", "Current public")
        record = {"id": RID, "path": "openwiki/notes/current.md", "content": public}
        event = {"id": EID, "before": private, "after": public}
        forbidden = forbidden_public_references([record], {RID: [event]}, [record], {RID: []})
        self.assertNotIn(RID, forbidden)
        self.assertIn(EID, forbidden)
        self.assertIn("Hidden revision title", forbidden)
        self.assertIn("Hidden revision body.", forbidden)

    def test_relative_markdown_links_are_hidden_or_rewritten_by_target(self):
        public_id = RID
        hidden_id = "123e4567-e89b-42d3-a456-426614174002"
        text = ("```md\n[code](private-note.md)\n```\n"
                "[click](index.md) [click](private-note.md#secret) [Visible](public-note.md)")
        links = [
            {"target_id": hidden_id, "fragment": "secret", "label": "Secret", "available": True},
            {"target_id": public_id, "fragment": None, "label": "Visible", "available": True},
        ]
        rewritten = _rewrite_markdown_links(
            text, links, {public_id}, "openwiki/notes/linked.md",
            {"openwiki/notes/private-note.md", "private-note.md"})
        self.assertEqual(rewritten,
                         "```md\n[code](private-note.md)\n```\n"
                         f"[click](index.md) Unavailable in this view [Visible](record:{public_id})")

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ProjectionError):
            validate_policy(b'{"schema_version":1,"schema_version":1}')


if __name__ == "__main__":
    unittest.main()
