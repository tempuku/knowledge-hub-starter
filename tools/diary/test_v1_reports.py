#!/usr/bin/env python3
"""Fast, non-browser negative and positive checks for browser evidence validation."""
import json
import tempfile
import unittest
from pathlib import Path
from validate_v1_reports import validate

HEAD = "a" * 40


class EvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.suite = self.root / "test_v1_ui.py"
        self.suite.write_text("class BrowserTests:\n    def test_one(self): pass\n    def test_two(self): pass\n")
        self.reports = self.root / "reports"
        self.reports.mkdir()
        self.write("chromium")
        self.write("webkit")

    def write(self, engine, **changes):
        report = {"kind": "synthetic-v1-browser-acceptance", "engine": engine,
                  "browser_version": "125", "playwright_version": "1.56.0",
                  "fixture_source_revision": "f" * 40, "generation": "b" * 64,
                  "tested_head_sha": HEAD,
                  "run": {"successful": True, "tests_run": 2, "failures": [], "errors": [], "skipped": []},
                  "tests": [{"name": "test_one", "status": "passed", "acceptance_ids": ["U1"]},
                            {"name": "test_two", "status": "passed", "acceptance_ids": ["U2"]}]}
        report.update(changes)
        (self.reports / f"{engine}-report.json").write_text(json.dumps(report))

    def test_both_engines_pass(self):
        summary = validate(self.reports, self.suite, HEAD)
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["test_count_per_engine"], 2)

    def test_missing_engine_rejected(self):
        (self.reports / "webkit-report.json").unlink()
        with self.assertRaisesRegex(ValueError, "Missing webkit"):
            validate(self.reports, self.suite, HEAD)

    def test_failed_test_rejected(self):
        report = json.loads((self.reports / "chromium-report.json").read_text())
        report["tests"][0]["status"] = "failed"
        (self.reports / "chromium-report.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "failed, skipped"):
            validate(self.reports, self.suite, HEAD)

    def test_head_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "revision differs"):
            validate(self.reports, self.suite, "c" * 40)

    def test_mixed_fixture_rejected(self):
        self.write("webkit", generation="c" * 64)
        with self.assertRaisesRegex(ValueError, "identical generated fixture"):
            validate(self.reports, self.suite, HEAD)

    def test_missing_case_rejected(self):
        report = json.loads((self.reports / "webkit-report.json").read_text())
        report["tests"].pop()
        (self.reports / "webkit-report.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "missing, duplicate"):
            validate(self.reports, self.suite, HEAD)


if __name__ == "__main__":
    unittest.main()
