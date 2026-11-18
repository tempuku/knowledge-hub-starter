"""Small real-Git generator regression; full P16 scale is a separate manual benchmark."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/projection"))
SPEC = importlib.util.spec_from_file_location("generate_p16_fixture", ROOT / "scripts/generate_p16_fixture.py")
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)
from build import publish
from git_source import load_revision


class P16GeneratorTests(unittest.TestCase):
    def test_infeasible_date_distribution_fails(self):
        with self.assertRaises(ValueError):
            generator.dates(10, 12, 2)
        with self.assertRaises(ValueError):
            generator.dates(10, 3, 10)

    def test_deterministic_writer_format_fixture_builds_real_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            source = parent / "source-one"
            report = generator.generate(source, records=8, events_per_record=3,
                                        date_count=5, busiest_day=3, reminder_count=4)
            self.assertEqual((report["records"], report["events"], report["dates"]), (8, 24, 5))
            self.assertEqual(report["max_depth"], 8)
            self.assertEqual(report["reminders"], 4)
            self.assertLess(abs(report["average_snapshot_bytes"] - 2048), 200)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
            self.assertEqual(report["source_revision"], head)
            commit, tree, records, histories, summaries = load_revision(source, "HEAD")
            self.assertEqual(commit, head)
            self.assertEqual(len(records), 8)
            self.assertEqual(len(histories), 8)
            self.assertEqual(len(summaries), 24)
            timestamps = [e["recorded_at"][:10] for event_list in histories.values() for e in event_list]
            self.assertEqual(len(set(timestamps)), 5)
            self.assertEqual(sum(value == "2025-01-01" for value in timestamps), 3)
            self.assertEqual(sum(len(record["reminders"]) for record in records), 4)
            self.assertTrue((source / "openwiki/projects/level-1/level-2/level-3"
                             "/level-4/level-5/level-6/level-7/index.md").is_file())

            destination = parent / "output"
            manifest = publish(source, destination, "HEAD", mode="private")
            catalog = json.loads((destination / "g" / manifest["generation"] / "catalog.json").read_text())
            self.assertEqual(catalog["record_count"], 8)
            self.assertEqual(catalog["event_count"], 24)

            again = generator.generate(parent / "source-two", records=8,
                                       events_per_record=3, date_count=5,
                                       busiest_day=3, reminder_count=4)
            self.assertEqual(report, again, "Source fixture must be commit- and byte-deterministic")


if __name__ == "__main__":
    unittest.main()
