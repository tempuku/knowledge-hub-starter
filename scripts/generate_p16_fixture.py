#!/usr/bin/env python3
"""Deterministic, synthetic P16 workload source for the approved P-05 fixture.

No real user records and no network. One Git commit contains canonical source,
writer-format history and writer-format index files. This is fixture generation,
not proof of a passing performance benchmark.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/projection"))
sys.path.insert(0, str(ROOT / "tools/records"))
from acceptance_fixture import GitFixture, uid
from service_v1 import _index_content

BASE_TIME = datetime(2025, 1, 1, tzinfo=timezone.utc)
TYPES = ("note", "project", "idea", "reference", "decision", "experiment")
STATUSES = ("draft", "in_progress", "completed", "deprecated")


def source(record_number: int, revision: int, *, record_id: str | None = None,
           reminder: bool = False, public: bool = False) -> str:
    """Near-2-KiB source with no common search token across different records."""
    fields = ["---"]
    if record_id is not None:
        fields.extend((f'id: "{record_id}"', "schema_version: 1"))
    status = STATUSES[record_number % len(STATUSES)] if revision == 9 else "stable"
    fields.extend((
        f"type: {TYPES[record_number % len(TYPES)]}",
        f'title: "Record-{record_number:06d}-Δ"',
        f"status: {status}",
        f"visibility: {'public' if public else 'private'}",
    ))
    if reminder:
        fields.append('reminders: [["2025-12-30", "Synthetic reminder"]]')
    fields.extend(("---", ""))
    prefix = "\n".join(fields) + "\n"
    token = f"payload{record_number:07d}revision{revision:02d}"
    # Each search term is record-specific. Duplicating a token within a record
    # does not create a huge common-token posting list in one 512-KiB shard.
    body_bytes = max(80, 2048 - len(prefix.encode("utf-8")) - 1)
    body = ((token + " ") * (body_bytes // (len(token) + 1) + 2))[:body_bytes]
    return prefix + body.rstrip() + "\n"


def record_path(number: int) -> str:
    depth = number % 8 + 1  # 1..8 directory segments, including area.
    segments = ["projects"] + [f"level-{index}" for index in range(1, depth)]
    return "openwiki/" + "/".join(segments) + f"/record-{number:06d}.md"


def dates(total: int, day_count: int, busiest_day: int) -> list[str]:
    if day_count < 2 or busiest_day <= 0 or busiest_day >= total or total - busiest_day < day_count - 1:
        raise ValueError("Fixture cannot distribute events across every requested date")
    counter = [0] * day_count
    timestamps = []
    for index in range(total):
        day = 0 if index < busiest_day else (
            1 + ((index - busiest_day) * (day_count - 1)) // (total - busiest_day)
        )
        counter[day] += 1
        if counter[day] > 86400:
            raise ValueError("More than 86400 events on one day; need second-precision redesign")
        stamp = BASE_TIME + timedelta(days=day, seconds=counter[day] - 1)
        timestamps.append(stamp.isoformat().replace("+00:00", "Z"))
    if sum(counter) != total or min(counter) == 0 or counter[0] != busiest_day:
        raise ValueError("Incorrect event date distribution")
    return timestamps


@contextlib.contextmanager
def deterministic_git_commit_dates():
    keys = ("GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE")
    old = {key: os.environ.get(key) for key in keys}
    try:
        for key in keys:
            os.environ[key] = "2025-01-01T00:00:00+00:00"
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def fill_indexes(fixture: GitFixture) -> None:
    """Index all depths with the same index renderer as the production writer."""
    directory_children: dict[str, set[str]] = {"openwiki": set()}
    for path in sorted(fixture.files):
        if not path.endswith(".md") or path.endswith(".log.md") or path.endswith("/index.md"):
            continue
        parent, filename = path.rsplit("/", 1)
        directory_children.setdefault(parent, set()).add(filename)
        while parent != "openwiki":
            parent, segment = parent.rsplit("/", 1)
            directory_children.setdefault(parent, set()).add(segment + "/")
    for parent, entries in directory_children.items():
        fixture.files[f"{parent}/index.md"] = _index_content(parent, entries)


def generate(destination: Path, *, records: int = 10000, events_per_record: int = 10,
             date_count: int = 365, busiest_day: int = 1000,
             reminder_count: int = 1000) -> dict:
    if records < 1 or events_per_record < 1 or not 0 <= reminder_count <= records:
        raise ValueError("Invalid fixture counts")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Destination must not exist or must be empty; never overwrite")
    total_events = records * events_per_record
    stamps = dates(total_events, date_count, busiest_day)
    fixture = GitFixture(destination)
    bytes_snapshots = 0
    reminder_set = set()
    for index in range(records):
        if index % len(STATUSES) != 3 and len(reminder_set) < reminder_count:
            reminder_set.add(index)
    if len(reminder_set) != reminder_count:
        # Tiny tests can use enough records and choose a smaller reminder target.
        raise ValueError("Not enough non-deprecated records for reminders")
    for index in range(records):
        rid = uid(fixture.next_id)  # The actual fixture writer assigns this next.
        is_public = index % 10 == 1
        candidate = source(index, 0, reminder=index in reminder_set, public=is_public)
        edits = []
        bytes_snapshots += len(candidate.encode("utf-8")) + 70  # approximate canonical create header
        for revision in range(1, events_per_record):
            # A smaller test may use fewer than ten revisions. Public/private
            # transitions occur for a subset; other records are always private.
            eligible = is_public and revision <= max(1, events_per_record // 2)
            updated = source(index, revision, record_id=rid,
                             reminder=index in reminder_set, public=eligible)
            bytes_snapshots += len(updated.encode("utf-8"))
            edits.append((updated, stamps[index + revision * records]))
        fixture.add_record(record_path(index), candidate,
                           recorded_at=stamps[index], edits=edits)
    fill_indexes(fixture)
    with deterministic_git_commit_dates():
        revision = fixture.commit("deterministic P16 synthetic fixture")
    snapshot_count = total_events
    count_dirs = max(len(path.split("/")) - 2 for path in fixture.files
                     if path.endswith(".md") and not path.endswith(".log.md"))
    source_bytes = sum(len(content.encode("utf-8")) for path, content in fixture.files.items()
                       if path.endswith(".md"))
    report = {
        "kind": "synthetic-p16-fixture",
        "source_revision": revision,
        "records": records, "events": total_events, "dates": date_count,
        "max_depth": count_dirs, "busiest_day_events": busiest_day,
        "reminders": len(reminder_set),
        "average_snapshot_bytes": round(bytes_snapshots / snapshot_count, 2),
        "source_bytes": source_bytes,
        "types": list(TYPES), "statuses": list(STATUSES),
        "immutable_base_date": "2025-01-01",
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--records", type=int, default=10000)
    parser.add_argument("--events-per-record", type=int, default=10)
    parser.add_argument("--dates", type=int, default=365)
    parser.add_argument("--busiest-day", type=int, default=1000)
    parser.add_argument("--reminders", type=int, default=1000)
    args = parser.parse_args()
    report = generate(args.destination, records=args.records,
                      events_per_record=args.events_per_record,
                      date_count=args.dates, busiest_day=args.busiest_day,
                      reminder_count=args.reminders)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
