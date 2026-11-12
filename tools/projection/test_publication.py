"""Regression tests for #32 policy input boundary."""
import json
import unittest
from pathlib import Path

from deterministic import ProjectionError
from publication import load_policy, validate_policy

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

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ProjectionError):
            validate_policy(b'{"schema_version":1,"schema_version":1}')


if __name__ == "__main__":
    unittest.main()
