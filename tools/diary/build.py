#!/usr/bin/env python3
"""Build a lazy-loading static diary from atomic OKF concepts.

The output has one calendar manifest, small per-day metadata shards,
and individual content JSON files. It never parses or serves log.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import date, datetime
from difflib import unified_diff
from pathlib import Path

import yaml
from icon import write_icons


ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "openwiki" / "journal"
SITE = ROOT / "site"
PAGE_SIZE = 50  # Fixed page budget; large days never become giant JSON responses.
NOTE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})/([a-z0-9][a-z0-9-]*)\.md$")
FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", flags=re.S)


def is_native_v1_log(source_log: str, entries: list[dict]) -> bool:
    """Recognize the v1 sibling-log envelope before legacy projection skips it.

    Strict v1 integrity validation runs separately; this keeps the transitional
    exporter from treating a legacy event as v1 merely because it carries extra
    fields with familiar names.
    """
    if not source_log.startswith("# Record history\n") or not entries:
        return False
    record_ids = set()
    for event in entries:
        if (type(event) is not dict or type(event.get("schema_version")) is not int or
                event.get("schema_version") != 1 or type(event.get("record_id")) is not str or
                type(event.get("id")) is not str):
            return False
        record_ids.add(event["record_id"])
    return len(record_ids) == 1


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def utc_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"Expected a UTC timestamp ending in Z: {value!r}")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def record_metadata(file: Path) -> dict:
    match = FRONT.match(file.read_text(encoding="utf-8"))
    return yaml.safe_load(match.group(1)) if match else {}


def parse_reminders(meta: dict, record: str) -> list[dict]:
    """A reminder is [ISO date/datetime or inclusive range, text]."""
    reminders = meta.get("reminders", []) or []
    if not isinstance(reminders, list):
        raise ValueError(f"reminders must be a list: {record}")
    result = []
    for item in reminders:
        if not isinstance(item, (list, tuple)) or len(item) != 2 or not isinstance(item[1], str) or not item[1].strip():
            raise ValueError(f"Expected [date_or_range, text]: {record}")
        when, label = item
        values = when if isinstance(when, list) else [when]
        if len(values) not in (1, 2):
            raise ValueError(f"Invalid reminder date range: {record}")
        normalized = []
        for value in values:
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            if not isinstance(value, str):
                raise ValueError(f"Invalid reminder date: {record}")
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                normalized.append(parsed.date().isoformat())
            except ValueError:
                normalized.append(date.fromisoformat(value).isoformat())
        if len(normalized) == 2 and normalized[0] > normalized[1]:
            raise ValueError(f"Reversed reminder date range: {record}")
        result.append({"start": normalized[0], "end": normalized[-1], "text": label.strip(), "record": record})
    return result


def build(output: Path, public_only: bool) -> tuple[int, int]:
    if output.resolve() == ROOT.resolve() or ROOT.resolve().is_relative_to(output.resolve()):
        raise ValueError("Output path cannot be the project root or its parent")
    if output.exists():
        shutil.rmtree(output)
    if public_only:
        # Fail closed: new source-side UI files must never silently become
        # public deployment assets. Copy only explicitly reviewed legacy assets.
        output.mkdir(parents=True)
        for name in ("index.html", "app.js", "style.css", "sw.js", "manifest.webmanifest"):
            shutil.copy2(SITE / name, output / name)
    else:
        shutil.copytree(SITE, output)
    if public_only:
        # Private project/repository links belong to the private source copy,
        # not a public preview even when no journal entries are published.
        index_file = output / "index.html"
        index = index_file.read_text(encoding="utf-8")
        marker = re.compile(
            r"<!-- BEGIN PRIVATE PROJECT LINKS -->.*?<!-- END PRIVATE PROJECT LINKS -->",
            flags=re.S,
        )
        if len(marker.findall(index)) != 1:
            raise ValueError("Expected exactly one private-links section in site/index.html")
        index_file.write_text(marker.sub("", index), encoding="utf-8")
    write_icons(output)

    by_day: dict[str, list[dict]] = defaultdict(list)
    native_records = {p.relative_to(ROOT).as_posix()[:-7] + ".md"
                      for p in (ROOT / "openwiki").rglob("*.log.md")}
    count = 0
    reminder_events = []
    for record_file in sorted((ROOT / "openwiki").rglob("*.md")):
        if record_file.name in {"index.md", "log.md"} or record_file.name.endswith(".log.md"):
            continue
        meta = record_metadata(record_file)
        if public_only and meta.get("visibility") != "public":
            continue
        reminder_events.extend(parse_reminders(meta, record_file.relative_to(ROOT).as_posix()))
    for file in sorted(NOTES.rglob("*.md")):
        rel = file.relative_to(NOTES).as_posix()
        match = NOTE.fullmatch(rel)
        if not match or file.name in {"index.md", "log.md"}:  # Ignore OKF catalog and log files
            continue
        day = "-".join(match.group(i) for i in (1, 2, 3))
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError(f"Invalid diary path date: {file}") from exc
        source = file.read_text(encoding="utf-8")
        parts = FRONT.match(source)
        if not parts:
            raise ValueError(f"Missing OKF frontmatter: {file}")
        meta = yaml.safe_load(parts.group(1))
        if not isinstance(meta, dict) or not meta.get("type") or not meta.get("title"):
            raise ValueError(f"Missing OKF entry type/title: {file}")
        if str(meta.get("occurred_on")) != day:
            raise ValueError(f"Date mismatch: {file}: occurred_on={meta.get('occurred_on')}")
        if public_only and meta.get("visibility", "private") != "public":
            continue
        record_id = f"{day}-{match.group(4)}"
        links = []
        for item in meta.get("sources", []) or []:
            if isinstance(item, dict) and isinstance(item.get("resource"), str):
                url = item["resource"]
                if url.startswith("https://") or url.startswith("http://"):
                    links.append({"title": item.get("title", url), "url": url})
        change = meta.get("change")
        change_payload = None
        if isinstance(change, dict):
            record = change.get("record")
            before = change.get("before")
            after = change.get("after")
            if not all(isinstance(x, str) for x in (record, before, after)):
                raise ValueError(f"Invalid change references: {file}")
            if not record.startswith("openwiki/") or ".." in Path(record).parts:
                raise ValueError(f"Unsafe source path: {record}")
            if not re.fullmatch(r"[0-9a-f]{40}", before):
                raise ValueError(f"Invalid before revision: {before}")
            if after != "SELF" and not re.fullmatch(r"[0-9a-f]{40}", after):
                raise ValueError(f"Invalid after revision: {after}")
            if record in native_records:
                # Native record-owned history supersedes legacy Git-diff diary entries.
                continue
            after_ref = "HEAD" if after == "SELF" else after
            diff = subprocess.run(
                ["git", "diff", "--no-ext-diff", before, after_ref, "--", record],
                cwd=ROOT, capture_output=True, text=True, check=True,
            ).stdout
            if not diff.strip():
                raise ValueError(f"Empty source diff: {file}")
            change_payload = {"record": record, "before": before, "after": after_ref,
                              "diff": diff, "source_url": "https://github.com/tempuku/knowledge-hub-starter/blob/" + after_ref + "/" + record}
        summary = {
            "id": record_id,
            "date": day,
            "title": meta["title"],
            "description": meta.get("description", ""),
            "project": meta.get("project", ""),
            "status": meta.get("status", "stable"),
            "tags": meta.get("tags", []),
            "links": links,
        }
        if "occurred_at" in meta:
            timestamp = utc_timestamp(meta["occurred_at"])
            if timestamp.date().isoformat() != day:
                raise ValueError(f"Timestamp date mismatch: {file}")
            summary["timestamp"] = timestamp.isoformat(timespec="microseconds")
        if change_payload:
            summary["has_change"] = True
        by_day[day].append(summary)
        body = source[parts.end():].strip()
        write_json(output / "data" / "entries" / (record_id + ".json"), {
            **summary, "body": body, "change": change_payload,
        })
        count += 1

    # Project authoritative sibling OKF logs into the same daily, lazy-loaded UI.
    # Existing journal notes remain for records that have not been migrated.
    log_pattern = re.compile(r"^## Entry ([a-z0-9-]+)\n\x60\x60\x60json\n(.*?)\n\x60\x60\x60(?:\n|$)", re.M | re.S)
    for log_file in sorted((ROOT / "openwiki").rglob("*.log.md")):
        source_log = log_file.read_text(encoding="utf-8")
        matches = list(log_pattern.finditer(source_log))
        if source_log.count("## Entry ") != len(matches):
            raise ValueError(f"Malformed log: {log_file}")
        entries = [json.loads(match.group(2)) for match in matches]
        for match, entry in zip(matches, entries):
            if entry.get("id") != match.group(1):
                raise ValueError(f"Log entry ID mismatch: {log_file}")
        # Native v1 logs are validated and projected by the separate v1
        # pipeline. This transitional legacy builder must not reinterpret
        # their schema or invent legacy record paths/diary rows.
        if is_native_v1_log(source_log, entries):
            continue
        for match, entry in zip(matches, entries):
            record = entry.get("record")
            if not isinstance(record, str) or not record.startswith("openwiki/") or ".." in Path(record).parts:
                raise ValueError(f"Unsafe record path: {log_file}")
            timestamp = utc_timestamp(entry.get("timestamp"))
            day = timestamp.date().isoformat()
            before, after = entry.get("before"), entry.get("after")
            if not isinstance(after, str) or (before is not None and not isinstance(before, str)):
                raise ValueError(f"Invalid snapshots: {log_file}")
            digest = lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None
            if digest(before) != entry.get("before_sha256") or digest(after) != entry.get("after_sha256"):
                raise ValueError(f"Snapshot hash mismatch: {log_file}")
            current_record = ROOT / record
            if not current_record.is_file() or current_record.resolve().is_relative_to((ROOT / "openwiki").resolve()) is False:
                raise ValueError(f"Missing or unsafe canonical record: {record}")
            current_source = current_record.read_text(encoding="utf-8")
            current_front = FRONT.match(current_source)
            current_meta = yaml.safe_load(current_front.group(1)) if current_front else {}
            if public_only and (entry.get("visibility") != "public" or current_meta.get("visibility") != "public"):
                continue
            record_id = "log-" + hashlib.sha256((record + ":" + entry["id"]).encode()).hexdigest()[:24]
            title = current_meta.get("title") or Path(record).stem
            action = entry.get("action", "UPDATED")
            description = entry.get("summary", "")
            if entry.get("provenance") == "git-backfill" or not description:
                description = f"{action.capitalize()} record"
            diff = "\n".join(unified_diff(
                (before or "").splitlines(), after.splitlines(),
                fromfile="Previous revision", tofile="This revision", n=2, lineterm="",
            ))
            summary = {"id": record_id, "date": day, "title": title,
                       "timestamp": timestamp.isoformat(timespec="microseconds"),
                       "description": description, "project": record,
                       "status": current_meta.get("status", "stable"),
                       "source_file": record if current_meta.get("visibility") == "public" else None,
                       "tags": ["history"], "links": [], "has_change": True}
            by_day[day].append(summary)
            write_json(output / "data" / "entries" / (record_id + ".json"), {
                **summary, "body": after,
                "change": {"record": record, "diff": diff},
                "log_entry": {key: value for key, value in entry.items() if key not in {"before", "after"}},
            })
            count += 1

    calendar = []
    for day in sorted(by_day, reverse=True):
        items = sorted(by_day[day], key=lambda v: v["id"])
        items.sort(key=lambda v: v.get("timestamp", ""), reverse=True)
        pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
        write_json(output / "data" / "days" / (day + ".json"), {
            "date": day, "count": len(items), "pages": pages, "page_size": PAGE_SIZE
        })
        for page in range(1, pages + 1):
            chunk = items[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
            write_json(output / "data" / "days" / day / (str(page) + ".json"), chunk)
        calendar.append({"date": day, "count": len(items)})
    write_json(output / "data" / "calendar.json", {
        "format": "knowledge-hub-calendar-v1",
        "days": calendar,
        "total": count,
    })
    write_json(output / "data" / "reminders.json", {"events": reminder_events})
    return count, len(calendar)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--public-only", action="store_true", help="Exclude private/unlabeled notes")
    args = parser.parse_args()
    output = (ROOT / args.output_dir).resolve()
    counts = build(output, args.public_only)
    print(f"Built {output}: {counts[0]} entries across {counts[1]} days (public_only={args.public_only})")


if __name__ == "__main__":
    main()
