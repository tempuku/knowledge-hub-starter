#!/usr/bin/env python3
"""Fail-closed local acceptance summary for generated-v1 Chromium + WebKit reports.

This checks browser-run evidence; it NEVER runs a browser or substitutes for iPad
hardware acceptance. Run only after both local browser suites have completed.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ENGINES = ("chromium", "webkit")


def required_tests(suite_path):
    tree = ast.parse(Path(suite_path).read_text(encoding="utf-8"))
    return {node.name for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, ast.FunctionDef)
            and node.name.startswith("test_")}


def validate(report_dir, suite_path, expected_head):
    report_dir = Path(report_dir)
    names = required_tests(suite_path)
    if not names:
        raise ValueError("No generated-v1 acceptance cases discovered")
    evidence = []
    for engine in ENGINES:
        path = report_dir / f"{engine}-report.json"
        if not path.is_file():
            raise ValueError(f"Missing {engine} report: {path}")
        raw = path.read_bytes()
        report = json.loads(raw)
        run = report.get("run") or {}
        tests = report.get("tests") or []
        actual = [test.get("name") for test in tests]
        if report.get("kind") != "synthetic-v1-browser-acceptance" or report.get("engine") != engine:
            raise ValueError(f"{engine}: unexpected report kind/engine")
        if not report.get("browser_version") or not report.get("playwright_version"):
            raise ValueError(f"{engine}: missing actual browser or Playwright version")
        if not report.get("fixture_source_revision") or not report.get("generation"):
            raise ValueError(f"{engine}: missing fixture revision or generation")
        if report.get("tested_head_sha") != expected_head:
            raise ValueError(f"{engine}: tested code revision differs from expected HEAD")
        if len(actual) != len(set(actual)) or set(actual) != names:
            raise ValueError(f"{engine}: missing, duplicate or unexpected cases: missing={sorted(names-set(actual))} extra={sorted(set(actual)-names)}")
        if not run.get("successful") or run.get("tests_run") != len(names):
            raise ValueError(f"{engine}: test runner was unsuccessful or incomplete")
        if any(test.get("status") != "passed" for test in tests):
            raise ValueError(f"{engine}: failed, skipped or unverified case")
        if run.get("failures") or run.get("errors") or run.get("skipped"):
            raise ValueError(f"{engine}: failing/error/skipped cases present")
        evidence.append({"engine": engine, "browser_version": report["browser_version"],
                         "playwright_version": report["playwright_version"],
                         "fixture_source_revision": report["fixture_source_revision"],
                         "generation": report["generation"], "tested_head_sha": expected_head,
                         "cases_passed": len(names),
                         "acceptance_ids": sorted({a for test in tests for a in test.get("acceptance_ids", [])}),
                         "report_sha256": hashlib.sha256(raw).hexdigest()})
    if len({item["fixture_source_revision"] for item in evidence}) != 1 or len({item["generation"] for item in evidence}) != 1:
        raise ValueError("Chromium and WebKit did not test the identical generated fixture")
    return {"kind": "generated-v1-local-browser-acceptance", "status": "passed",
            "tested_head_sha": expected_head, "test_count_per_engine": len(names),
            "browser_evidence": evidence,
            "physical_ipad_status": "not-verified-by-browser-suite"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reports-dir", required=True, type=Path)
    p.add_argument("--suite", type=Path, default=Path(__file__).with_name("test_v1_ui.py"))
    p.add_argument("--head", required=True, help="Exact git HEAD tested in the local checkout")
    args = p.parse_args()
    try:
        summary = validate(args.reports_dir, args.suite, args.head)
    except (ValueError, OSError, json.JSONDecodeError, SyntaxError) as exc:
        raise SystemExit(f"Local generated-v1 acceptance NOT VERIFIED: {exc}") from exc
    output = args.reports_dir / "local-v1-acceptance-summary.json"
    output.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"Local generated-v1 browser acceptance passed; evidence: {output}")


if __name__ == "__main__":
    main()
