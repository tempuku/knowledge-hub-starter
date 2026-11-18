"""Regression tests for the issue #37 evidence gate; no user data or browser required."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_integrated_acceptance", ROOT / "scripts/check_integrated_acceptance.py"
)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class IntegratedAcceptanceGateTests(unittest.TestCase):
    def setUp(self):
        self.ids = gate.contract_ids(gate.CONTRACT.read_text(encoding="utf-8"))
        self.report = json.loads(gate.REPORT.read_text(encoding="utf-8"))

    def test_all_sixty_scenarios_exist_and_pending_matrix_is_structurally_valid(self):
        self.assertEqual(len(self.ids), 60)
        self.assertEqual(set(self.report["scenarios"]), set(self.ids))
        self.assertEqual([], gate.validate(self.report, self.ids))
        self.assertTrue(gate.validate(self.report, self.ids, require_complete=True))

    def test_contract_drift_or_missing_row_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Contract drift"):
            gate.contract_ids(gate.CONTRACT.read_text(encoding="utf-8").replace("| U24 |", "| U25 |"))
        broken = copy.deepcopy(self.report)
        del broken["scenarios"]["S1"]
        self.assertTrue(any("Matrix ID mismatch" in e for e in gate.validate(broken, self.ids)))

    def test_unknown_and_unbacked_pass_cannot_be_reported(self):
        broken = copy.deepcopy(self.report)
        broken["scenarios"]["S1"]["status"] = "green"
        self.assertTrue(any("S1: status" in e for e in gate.validate(broken, self.ids)))
        broken["scenarios"]["S1"]["status"] = "passed"
        self.assertTrue(any("S1: passed without evidence" in e for e in gate.validate(broken, self.ids)))
        for key in ("command", "fixture_revision", "expected", "observed"):
            self.assertTrue(any(f"S1: passed without {key}" in e for e in gate.validate(broken, self.ids)))

    def test_predecessor_cannot_be_claimed_complete_without_evidence(self):
        broken = copy.deepcopy(self.report)
        broken["dependencies"]["69"]["status"] = "passed"
        self.assertTrue(any("Dependency #69: missing completion evidence" in e for e in gate.validate(broken, self.ids)))

    def test_performance_limits_fail_closed(self):
        benchmark = {
            "fixture": {
                "records": 10000, "events": 100000, "dates": 365, "max_depth": 8,
                "busiest_day_events": 1000, "reminders": 1000,
                "average_snapshot_bytes": 2048, "source_bytes": 300000000,
            },
            "environment": {
                "runner": "synthetic test only", "cpu_model": "fixture", "cpu_cores": 4,
                "ram_gib": 8, "browser_chromium": "test", "browser_webkit": "test",
                "network_mbit": 10, "rtt_ms": 100, "cpu_slowdown": 4,
            },
            "build_runs": [
                {"seconds": 110, "peak_rss_bytes": 800000000},
                {"seconds": 125, "peak_rss_bytes": 900000000},
                {"seconds": 130, "peak_rss_bytes": 1200000000},
            ],
            "diary_after_manifest_ms": [1800, 2100, 2200],
            "record_after_response_ms": [900, 1100, 1300],
            "transfer_bytes": {"diary": 10240, "record": 40960},
        }
        failures = gate.check_performance(benchmark)
        self.assertTrue(any("median build time" in e for e in failures))
        self.assertTrue(any("diary_after_manifest_ms" in e for e in failures))
        self.assertTrue(any("record_after_response_ms" in e for e in failures))
        benchmark["build_runs"] = [
            {"seconds": 110, "peak_rss_bytes": 800000000},
            {"seconds": 112, "peak_rss_bytes": 900000000},
            {"seconds": 118, "peak_rss_bytes": 1000000000},
        ]
        benchmark["diary_after_manifest_ms"] = [1800, 1900, 1950]
        benchmark["record_after_response_ms"] = [800, 900, 950]
        self.assertEqual([], gate.check_performance(benchmark))


if __name__ == "__main__":
    unittest.main()
