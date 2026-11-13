"""Fail-closed tests for legacy snapshot comparison."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from inventory_legacy import check_snapshots


class SnapshotInventoryTests(unittest.TestCase):
    def test_malformed_paired_log_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "openwiki/notes").mkdir(parents=True)
            (root / "openwiki/notes/a.md").write_text("source\n")
            (root / "openwiki/notes/a.log.md").write_text(
                "# History\n\n## Entry malformed\n```json\n{\\\"after\\\": }\n```\n")
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                            "commit", "-qm", "fixture"], cwd=root, check=True)
            self.assertGreater(check_snapshots("HEAD", root), 0)


if __name__ == "__main__":
    unittest.main()
