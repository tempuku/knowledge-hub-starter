#!/usr/bin/env python3
"""P16 three-clean-run native projection benchmark, with no simulated timings.

Run against scripts/generate_p16_fixture.py's real-Git source on a documented
4-core/8-GiB runner. Browser metrics are a separate local Playwright step.
The report remains incomplete until measured Chromium/WebKit timings arrive.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/projection"))
from build import publish

EXPECTED = {
    "records": 10000, "events": 100000, "dates": 365,
    "max_depth": 8, "busiest_day_events": 1000, "reminders": 1000,
}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def runner_environment() -> dict:
    cpu_name = platform.processor() or "unknown"
    if sys.platform.startswith("linux"):
        try:
            cpu_name = next(
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            )
        except (FileNotFoundError, StopIteration):
            pass
        try:
            memory_kib = int(next(
                line.split()[1]
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemTotal:")
            ))
            ram_gib = round(memory_kib * 1024 / (1024 ** 3), 2)
        except (FileNotFoundError, StopIteration, ValueError):
            ram_gib = None
    else:
        ram_gib = None
    cores = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    return {
        "runner": platform.platform(),
        "cpu_model": cpu_name,
        "cpu_cores": cores,
        "ram_gib": ram_gib,
        "browser_chromium": None,
        "browser_webkit": None,
        "network_mbit": None,
        "rtt_ms": None,
        "cpu_slowdown": None,
        "python": platform.python_version(),
    }


def run_child(source: Path, destination: Path, revision: str) -> None:
    start = time.perf_counter()
    manifest = publish(source, destination, revision, mode="private")
    elapsed = time.perf_counter() - start
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform.startswith("linux"):
        maxrss *= 1024  # Linux ru_maxrss is in KiB; macOS is in bytes.
    print(json.dumps({
        "seconds": round(elapsed, 3),
        "peak_rss_bytes": maxrss,
        "generation": manifest["generation"],
        "source_revision": manifest["source_revision"],
        "mode": manifest["mode"],
    }))


def benchmark(source: Path, fixture_report: dict, output_dir: Path, *,
              enforce_full_scale: bool = True) -> dict:
    if fixture_report.get("kind") != "synthetic-p16-fixture":
        raise ValueError("Not a trusted P16 synthetic fixture report")
    if enforce_full_scale and any(fixture_report.get(k) != v for k, v in EXPECTED.items()):
        raise ValueError("P16 benchmark requires full 10k/100k/365 fixture; do not reduce counts")
    revision = git(source, "rev-parse", "HEAD")
    if fixture_report.get("source_revision") != revision:
        raise ValueError("Fixture report is stale; Git HEAD has changed")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Benchmark outputs must use a new empty directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    for index in range(3):
        destination = output_dir / f"build-{index + 1}"
        command = [
            sys.executable, str(Path(__file__).resolve()),
            "--child", "--source", str(source),
            "--destination", str(destination),
            "--revision", revision,
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"P16 build {index + 1} failed: {result.stderr[-1600:]}")
        record = json.loads(result.stdout)
        if record["source_revision"] != revision or record["mode"] != "private":
            raise RuntimeError("P16 build used an incorrect source revision or mode")
        runs.append({"seconds": record["seconds"], "peak_rss_bytes": record["peak_rss_bytes"]})
        # These are generated synthetic artifacts, not canonical source. Keep only
        # the run evidence to avoid keeping three large unreviewed data copies.
        shutil.rmtree(destination)
    return {
        "fixture": {key: fixture_report[key] for key in
                    (*EXPECTED.keys(), "average_snapshot_bytes", "source_bytes")},
        "environment": runner_environment(),
        "build_runs": runs,
        "diary_after_manifest_ms": [],
        "record_after_response_ms": [],
        "transfer_bytes": {},
        "fixture_source_revision": revision,
        "benchmark_tool": "scripts/benchmark_p16.py",
        "browser_status": "pending-local-throttled-playwright",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--fixture-report", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--destination", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--revision", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.child:
            if not args.destination or not args.revision:
                raise ValueError("child run requires destination and revision")
            run_child(args.source.resolve(), args.destination.resolve(), args.revision)
            return 0
        if not args.fixture_report or not args.output_dir or not args.report:
            raise ValueError("Must supply --source, --fixture-report, --output-dir, --report")
        fixture = json.loads(args.fixture_report.read_text(encoding="utf-8"))
        observed = benchmark(args.source.resolve(), fixture, args.output_dir.resolve())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(observed, indent=2))
        # Don't exit success as P16 complete: browser budget evidence is missing.
        print("Build measurements written; P16 acceptance still needs local throttled browser results.", file=sys.stderr)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"P16 benchmark failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
