"""Native log strictness tests, including corruption and canonical mismatch."""
import hashlib
import json
import unittest
import uuid

from native_logs import parse_log
from deterministic import ProjectionError


def uid(i):
    return str(uuid.UUID(int=(1 << 76) | (2 << 62) | i))


def digest(value):
    return None if value is None else hashlib.sha256(value.encode()).hexdigest()


def event(i, before, after, previous=None):
    return {
        "schema_version": 1, "id": uid(i), "record_id": uid(100),
        "operation_id": uid(200 + i), "sequence": i,
        "action": "CREATED" if i == 1 else "UPDATED",
        "recorded_at": "2026-11-12T10:00:00Z",
        "occurred_on": None, "occurred_at": None,
        "actor": {"id": "agent", "kind": "agent", "label": "Agent"},
        "summary": "Change", "path_before": None if i == 1 else "openwiki/notes/a.md",
        "path_after": "openwiki/notes/a.md",
        "before": before, "after": after,
        "before_sha256": digest(before), "after_sha256": digest(after),
        "previous_event_id": previous, "idempotency_key": uid(300 + i),
        "request_sha256": "0" * 64,
        "provenance": {"kind": "native", "source_ref": None, "original_time": None},
    }


def log(*events):
    return "# Record history\n" + "".join(
        "\n## Entry " + e["id"] + "\n\x60\x60\x60json\n" +
        json.dumps(e, indent=2) + "\n\x60\x60\x60\n" for e in events
    )


class NativeLogTests(unittest.TestCase):
    def test_valid_two_event_chain(self):
        a = event(1, None, "first\n")
        b = event(2, "first\n", "second\n", a["id"])
        self.assertEqual(len(parse_log(log(a, b), canonical="second\n",
                                       canonical_path="openwiki/notes/a.md")), 2)

    def test_digest_mismatch_rejected(self):
        a = event(1, None, "first\n")
        a["after"] = "tampered\n"
        with self.assertRaises(ProjectionError):
            parse_log(log(a))

    def test_chain_break_rejected(self):
        a = event(1, None, "first\n")
        b = event(2, "wrong\n", "second\n", a["id"])
        with self.assertRaises(ProjectionError):
            parse_log(log(a, b))

    def test_unmatched_trailing_text_rejected(self):
        a = event(1, None, "first\n")
        with self.assertRaises(ProjectionError):
            parse_log(log(a) + "unmatched\n")

    def test_duplicate_json_key_rejected(self):
        a = event(1, None, "first\n")
        malformed = log(a).replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,')
        with self.assertRaises(ProjectionError):
            parse_log(malformed)

    def test_canonical_mismatch_rejected(self):
        with self.assertRaises(ProjectionError):
            parse_log(log(event(1, None, "first\n")), canonical="other\n")

    def test_empty_header_rejected(self):
        with self.assertRaises(ProjectionError):
            parse_log("# Record history\n")


if __name__ == "__main__":
    unittest.main()
