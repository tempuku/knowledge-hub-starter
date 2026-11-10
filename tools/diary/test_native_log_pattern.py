#!/usr/bin/env python3
"""Regression: Markdown log entries are recognized and projected by the diary builder."""
import hashlib
import json
import re
import unittest

PATTERN = re.compile(r"^## Entry ([a-z0-9-]+)\n\x60\x60\x60json\n(.*?)\n\x60\x60\x60(?:\n|$)", re.M | re.S)


class NativeLogTests(unittest.TestCase):
    def test_multiple_entries_same_day(self):
        entries = []
        for identifier in ("demo-baseline-20261110", "demo-native-update-20261110"):
            after = "record content"
            payload = {
                "id": identifier,
                "timestamp": "2026-11-10T17:38:34Z",
                "after": after,
                "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
            }
            entries.append("## Entry " + identifier + "\n\x60\x60\x60json\n" + json.dumps(payload) + "\n\x60\x60\x60\n")
        matches = list(PATTERN.finditer("\n".join(entries)))
        self.assertEqual(len(matches), 2)
        self.assertEqual([json.loads(m.group(2))["id"] for m in matches],
                         ["demo-baseline-20261110", "demo-native-update-20261110"])


if __name__ == "__main__":
    unittest.main()
