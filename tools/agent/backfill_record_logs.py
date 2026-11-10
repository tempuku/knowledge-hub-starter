#!/usr/bin/env python3
"""Reconstruct missing record-owned logs from Git commits; never rewrite existing logs."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPENWIKI = ROOT / "openwiki"
ENTRY = re.compile(r"^## Entry ([a-z0-9-]+)\n\x60\x60\x60json\n(.*?)\n\x60\x60\x60(?:\n|$)", re.M | re.S)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def digest(value: str | None) -> str | None:
    return hashlib.sha256(value.encode()).hexdigest() if value is not None else None


def at_commit(commit: str, path: str) -> str | None:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True)
    return result.stdout.decode("utf-8") if result.returncode == 0 else None


def history(path: str) -> list[dict]:
    # --follow handles renames; preserve Git's commit chronology.
    shas = git("log", "--follow", "--format=%H", "--", path).splitlines()[::-1]
    events = []
    previous = None
    for sha in shas:
        current = at_commit(sha, path)
        if current is None:
            # A rename may have happened: avoid inventing snapshots.
            continue
        if current == previous:
            continue
        stamp = git("show", "-s", "--format=%cI", sha).strip()
        timestamp = dt.datetime.fromisoformat(stamp).astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        summary = git("show", "-s", "--format=%s", sha).strip()
        actor = git("show", "-s", "--format=%an", sha).strip()
        visibility = re.search(r"(?m)^visibility:\s*(\S+)", current)
        events.append({
            "id": "git-" + sha[:16], "timestamp": timestamp, "actor": actor,
            "action": "CREATED" if previous is None else "UPDATED",
            "summary": summary or "Historical Git revision", "record": path,
            "visibility": visibility.group(1).strip("\"'") if visibility else "private",
            "before": previous, "after": current,
            "before_sha256": digest(previous), "after_sha256": digest(current),
            "source_commit": sha, "provenance": "git-backfill",
        })
        previous = current
    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write missing logs; default is dry run")
    args = parser.parse_args()
    counts = {"created": 0, "skipped": 0, "events": 0, "mismatches": 0}
    for path in sorted(OPENWIKI.rglob("*.md")):
        if path.name in {"index.md", "log.md"} or path.name.endswith(".log.md"):
            continue
        relative = path.relative_to(ROOT).as_posix()
        log = path.with_name(path.stem + ".log.md")
        if log.exists():
            counts["skipped"] += 1
            continue
        events = history(relative)
        current = path.read_text(encoding="utf-8")
        if not events or events[-1]["after"] != current:
            # The log must be continuous and end at the actual current record.
            counts["mismatches"] += 1
            print("SKIP mismatched history:", relative)
            continue
        content = "# OKF Record Change Log\n\n" + "\n".join(
            "## Entry " + e["id"] + "\n\x60\x60\x60json\n" +
            json.dumps(e, ensure_ascii=False, indent=2) + "\n\x60\x60\x60\n"
            for e in events
        )
        if args.write:
            log.write_text(content, encoding="utf-8")
        counts["created"] += 1
        counts["events"] += len(events)
        print(("WRITE" if args.write else "WOULD WRITE"), relative, len(events), "events")
    print(json.dumps(counts))
    if counts["mismatches"]:
        raise SystemExit("Some records require manual review; history not invented")


if __name__ == "__main__":
    main()
