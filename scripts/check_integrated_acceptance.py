#!/usr/bin/env python3
"""Fail-closed evidence index for issue #37's S/P/U integrated acceptance.

This is an evidence *validator*, not a test runner. A pending matrix is valid
during development, but --require-complete fails until all 60 real scenarios,
predecessors and P16 measurements have evidence for the exact checkout head.
Never commit raw private record content or browser cache data to this report.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "openwiki/design/acceptance.md"
REPORT = ROOT / "docs/acceptance/integrated-evidence.json"
BASELINE = "5befec6cc67486327fa36b22f54f22db59cceecb"
EXPECTED = [f"S{i}" for i in range(1, 21)] + [f"P{i}" for i in range(1, 17)] + [f"U{i}" for i in range(1, 25)]
DEPENDENCIES = ("36", "40", "69")


def contract_ids(markdown: str) -> list[str]:
    found = [
        m.group(1)
        for line in markdown.splitlines()
        if (m := re.match(r"^\|\s*([SPU]\d+)\s*\|", line))
    ]
    if len(found) != 60 or set(found) != set(EXPECTED) or len(set(found)) != 60:
        raise ValueError(
            f"Contract drift: expected exactly S1-S20, P1-P16, U1-U24; found {found}"
        )
    return found


def empty_report() -> dict:
    return {
        "schema_version": 1,
        "contract_commit": BASELINE,
        "tested_head": None,
        "ci_run_url": None,
        "fixture_revision": None,
        "environment": {},
        "dependencies": {issue: {"status": "pending", "evidence": []} for issue in DEPENDENCIES},
        "agent_client": {"name": None, "version": None, "transcript": None},
        "performance": {},
        "physical_ipad_status": "unverified",
        "scenarios": {
            item: {
                "status": "pending",
                "command": None,
                "fixture_revision": None,
                "expected": None,
                "observed": None,
                "evidence": [],
            }
            for item in EXPECTED
        },
    }


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def check_performance(data: object) -> list[str]:
    """Require actual P-05 fixture, environment, 3 runs and numeric budgets."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["P16: performance report must be an object"]
    fixture = data.get("fixture")
    sizes = {
        "records": 10000, "events": 100000, "dates": 365,
        "max_depth": 8, "busiest_day_events": 1000, "reminders": 1000,
    }
    if not isinstance(fixture, dict):
        errors.append("P16: missing fixture counts")
    else:
        for key, expected in sizes.items():
            if fixture.get(key) != expected:
                errors.append(f"P16: fixture {key} must be {expected}")
        avg = fixture.get("average_snapshot_bytes")
        if not isinstance(avg, (int, float)) or isinstance(avg, bool) or not 1800 <= avg <= 2300:
            errors.append("P16: measured average snapshot must be approximately 2 KiB")
        if not isinstance(fixture.get("source_bytes"), int) or fixture["source_bytes"] <= 0:
            errors.append("P16: source bytes must be measured")
    env = data.get("environment")
    if not isinstance(env, dict):
        errors.append("P16: missing benchmark environment")
    else:
        for key in ("runner", "cpu_model", "browser_chromium", "browser_webkit"):
            if not nonempty(env.get(key)):
                errors.append(f"P16: missing environment {key}")
        for key, expected in {
            "cpu_cores": 4, "ram_gib": 8, "network_mbit": 10,
            "rtt_ms": 100, "cpu_slowdown": 4,
        }.items():
            if env.get(key) != expected:
                errors.append(f"P16: expected documented test profile {key}={expected}")
    runs = data.get("build_runs")
    if not isinstance(runs, list) or len(runs) != 3:
        errors.append("P16: three clean build runs required")
    else:
        for index, run in enumerate(runs):
            if not isinstance(run, dict):
                errors.append(f"P16: build run {index + 1} malformed")
                continue
            for key in ("seconds", "peak_rss_bytes"):
                value = run.get(key)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                    errors.append(f"P16: build run {index + 1} lacks {key}")
        if not any(x.startswith("P16: build run ") for x in errors):
            if statistics.median(r["seconds"] for r in runs) > 120:
                errors.append("P16: median build time exceeds 120 seconds")
            if statistics.median(r["peak_rss_bytes"] for r in runs) > 1024 ** 3:
                errors.append("P16: median peak RSS exceeds 1 GiB")
    for metric, budget in (
        ("diary_after_manifest_ms", 2000),
        ("record_after_response_ms", 1000),
    ):
        values = data.get(metric)
        if (not isinstance(values, list) or len(values) != 3
                or any(not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0 for v in values)):
            errors.append(f"P16: {metric} requires three measured samples")
        elif statistics.median(values) > budget:
            errors.append(f"P16: median {metric} exceeds {budget} ms")
    if not isinstance(data.get("transfer_bytes"), dict) or not data["transfer_bytes"]:
        errors.append("P16: actual browser transfer bytes required")
    return errors


def validate(report: object, ids: list[str], *, require_complete: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["Report must be a JSON object"]
    if report.get("schema_version") != 1:
        errors.append("Unsupported report schema_version")
    if report.get("contract_commit") != BASELINE:
        errors.append("Immutable contract SHA mismatch")
    matrix = report.get("scenarios")
    if not isinstance(matrix, dict):
        return errors + ["Missing scenarios object"]
    if set(matrix) != set(ids):
        missing, extra = set(ids) - set(matrix), set(matrix) - set(ids)
        errors.append(f"Matrix ID mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    for sid in ids:
        entry = matrix.get(sid)
        if not isinstance(entry, dict):
            errors.append(f"{sid}: missing scenario object")
            continue
        state = entry.get("status")
        if state not in ("pending", "passed", "failed"):
            errors.append(f"{sid}: status must be pending, passed or failed")
            continue
        if state == "passed":
            for key in ("command", "fixture_revision", "expected", "observed"):
                if not nonempty(entry.get(key)):
                    errors.append(f"{sid}: passed without {key}")
            evidence = entry.get("evidence")
            if not isinstance(evidence, list) or not evidence or not all(nonempty(x) for x in evidence):
                errors.append(f"{sid}: passed without evidence links")
        if require_complete and state != "passed":
            errors.append(f"{sid}: not passed ({state})")
    deps = report.get("dependencies")
    if not isinstance(deps, dict) or set(deps) != set(DEPENDENCIES):
        errors.append("Dependencies must include exactly issues #36, #40 and #69")
    else:
        for issue in DEPENDENCIES:
            value = deps[issue]
            if not isinstance(value, dict) or value.get("status") not in ("pending", "passed", "failed"):
                errors.append(f"Dependency #{issue}: invalid status")
            elif value["status"] == "passed" and (
                not isinstance(value.get("evidence"), list) or not value["evidence"]
                or not all(nonempty(x) for x in value["evidence"])
            ):
                errors.append(f"Dependency #{issue}: missing completion evidence")
            elif require_complete and value["status"] != "passed":
                errors.append(f"Dependency #{issue}: not passed")
    if require_complete:
        head = report.get("tested_head")
        if not nonempty(head) or not re.fullmatch("[0-9a-f]{40}", head):
            errors.append("Missing 40-hex exact tested_head")
        else:
            try:
                if git_head() != head:
                    errors.append("Evidence head differs from checkout HEAD")
            except (OSError, subprocess.CalledProcessError):
                errors.append("Unable to verify checkout HEAD")
        if not nonempty(report.get("fixture_revision")):
            errors.append("Missing integrated fixture revision")
        run_url = report.get("ci_run_url")
        if not nonempty(run_url) or not re.fullmatch(
            r"https://github\.com/tempuku/knowledge-hub-starter/actions/runs/\d+",
            run_url,
        ):
            errors.append("Missing exact-head required GitHub Actions run")
        agent = report.get("agent_client")
        if not isinstance(agent, dict) or not all(
            nonempty(agent.get(k)) for k in ("name", "version", "transcript")
        ):
            errors.append("Missing actual agent-client version and session transcript")
        if not isinstance(report.get("environment"), dict) or not report["environment"]:
            errors.append("Missing integrated environment details")
        if report.get("physical_ipad_status") not in ("unverified", "verified"):
            errors.append("Physical iPad status must be explicitly verified or unverified")
        errors.extend(check_performance(report.get("performance")))
        if matrix.get("P16", {}).get("status") != "passed":
            errors.append("P16 not accepted")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--init", action="store_true", help="print a pending 60-row JSON matrix")
    parser.add_argument("--require-complete", action="store_true", help="fail on missing evidence and performance budgets")
    args = parser.parse_args()
    try:
        ids = contract_ids(args.contract.read_text(encoding="utf-8"))
        if args.init:
            print(json.dumps(empty_report(), indent=2) + "\n", end="")
            return 0
        report = json.loads(args.report.read_text(encoding="utf-8"))
        errors = validate(report, ids, require_complete=args.require_complete)
        counts = {
            status: sum(row.get("status") == status for row in report.get("scenarios", {}).values()
                        if isinstance(row, dict))
            for status in ("passed", "pending", "failed")
        }
        print(json.dumps({"scenarios": len(ids), "counts": counts, "strict": args.require_complete, "errors": errors}, indent=2))
        return 1 if errors else 0
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"Integrated acceptance gate failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
