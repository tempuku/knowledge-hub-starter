"""Regression tests for #32 policy input boundary."""
import json
import unittest
from pathlib import Path

from deterministic import ProjectionError
from publication import load_policy, validate_policy, select_public, audit_public

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
            return "---\\nschema_version: 1\\nvisibility: " + visibility + "\\n---\\nbody\\n"
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
        record = {"id": RID, "content": "---\\nvisibility: public\\n---\\nbody\\n"}
        records, histories, summaries = select_public([record], {RID: []}, {}, policy)
        self.assertEqual((records, histories, summaries), ([], {}, {}))

    def test_public_byte_audit_detects_ids_and_paths(self):
        for leak in ('private-id', 'openwiki/notes/secret.md'):
            with self.assertRaises(ProjectionError):
                audit_public({"catalog.json": json.dumps({"x": leak}).encode()}, {leak})

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ProjectionError):
            validate_policy(b'{"schema_version":1,"schema_version":1}')


if __name__ == "__main__":
    unittest.main()
