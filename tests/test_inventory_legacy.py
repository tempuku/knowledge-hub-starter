"""Regression tests for the frozen-source inventory (issue #35).

Run: python3 -m unittest discover -s tests -p 'test_inventory_legacy.py'
These tests do not certify human review, migration, or publication.
"""
import hashlib
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inventory_legacy", ROOT / "scripts" / "inventory_legacy.py")
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def test_frozen_bytes_and_fail_closed_dispositions(self):
        paths = [
            "openwiki/index.md",
            "openwiki/area/index.md",
            "openwiki/area/topic.md",
            "openwiki/area/topic.log.md",
            "openwiki/journal/2026/11/09/log.md",
        ]
        contents = {p: ("content:" + p).encode("utf-8") for p in paths}

        def git(*args):
            self.assertEqual(args[:3], ("ls-tree", "-r", "--name-only"))
            self.assertEqual(args[3], "frozen")
            return "\n".join(paths)

        def check_output(args, **kwargs):
            self.assertEqual(args[-2], "show")
            rev, path = args[-1].split(":", 1)
            self.assertEqual(rev, "frozen")
            return contents[path]

        with patch.object(inventory, "git", side_effect=git), patch.object(
            inventory.subprocess, "check_output", side_effect=check_output
        ):
            result = inventory.build("frozen")
            repeat = inventory.build("frozen")

        self.assertEqual(result, repeat)
        self.assertEqual(result["review_status"], "pending")
        self.assertEqual(len(result["items"]), 3)
        self.assertEqual(
            [item["old_path"] for item in result["items"]],
            sorted(p for p in paths if not p.endswith("/index.md")),
        )
        for item in result["items"]:
            self.assertIsNone(item["disposition"])
            self.assertIsNone(item["allocated_record_id"])
            self.assertIsNone(item["destination_path"])
            self.assertIsNone(item["project_mapping"])
            self.assertEqual(
                item["source_sha256"], hashlib.sha256(contents[item["old_path"]]).hexdigest()
            )
        record = next(i for i in result["items"] if i["old_path"].endswith("topic.md"))
        self.assertEqual(record["legacy_log_path"], "openwiki/area/topic.log.md")

    def test_native_directory_log_keeps_identity(self):
        with patch.object(inventory, "git", return_value="openwiki/journal/2026/11/09/log.md"), patch.object(
            inventory.subprocess, "check_output", return_value=b"unique summary"
        ):
            item = inventory.build("frozen")["items"][0]
        self.assertEqual(item["legacy_log_path"], item["old_path"])
        self.assertIsNone(item["disposition"])  # never silently discard human prose


if __name__ == "__main__":
    unittest.main()
