#!/usr/bin/env python3
"""Local agent write adapter: atomic OKF + diary commit with Git provenance.

This is a CLI reference implementation, NOT an authenticated network MCP server.
Run only in a trusted checkout; authorization must be provided by the caller.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def publish(request):
    """Publish an existing OKF record revision and one dated journal record.

    Caller must stage no unrelated changes; only two exact paths are committed.
    """
    record = request["record"]
    path = (ROOT / record).resolve()
    if not path.is_relative_to((ROOT / "openwiki").resolve()):
        raise ValueError("Record must be inside openwiki")
    if not path.is_file() or path.suffix != ".md":
        raise ValueError("Existing Markdown record required")
    if git("status", "--porcelain"):
        raise ValueError("Working tree must be clean before publish")
    expected = request["expected_head"]
    if git("rev-parse", "HEAD") != expected:
        raise ValueError("Stale expected_head")
    key = request["idempotency_key"]
    if not SLUG.fullmatch(key):
        raise ValueError("Invalid idempotency key")
    today = dt.date.today().isoformat()
    journal = ROOT / "openwiki" / "journal" / today.replace("-", "/") / (key + ".md")
    if journal.exists():
        raise ValueError("Idempotency key already exists; inspect prior journal before retrying")
    old = path.read_text(encoding="utf-8")
    new = request["content"]
    match = FRONT.match(new)
    if not match:
        raise ValueError("Missing OKF frontmatter")
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict) or not meta.get("type") or not meta.get("title"):
        raise ValueError("Invalid OKF metadata")
    if meta.get("visibility", "private") != "public":
        raise ValueError("Private writes require a private repository; refusing public checkout")
    if new == old:
        raise ValueError("No semantic change")
    summary = request["summary"].strip()
    if not summary or len(summary) > 240:
        raise ValueError("Summary must contain 1-240 characters")
    actor = request["actor"].strip()
    if not actor or "\n" in actor:
        raise ValueError("Actor required")
    journal.parent.mkdir(parents=True, exist_ok=True)
    index = journal.parent / "index.md"
    index_old = index.read_text(encoding="utf-8") if index.exists() else "# " + today + " — diary records\n"
    if ("(" + journal.name + ")") in index_old:
        raise ValueError("Journal record already indexed")
    source_url = "https://github.com/tempuku/knowledge-hub-starter/blob/main/" + record
    entry_meta = {
        "type": "journal",
        "title": "Updated: " + str(meta["title"]),
        "description": summary,
        "occurred_on": today,
        "visibility": "public",
        "actor": actor,
        "change": {"record": record, "before": expected, "after": "SELF"},
        "sources": [{"title": "Original record", "resource": source_url}],
    }
    entry = "---\n" + yaml.safe_dump(entry_meta, sort_keys=False, allow_unicode=True) + "---\n\n" + summary + "\n"
    try:
        path.write_text(new, encoding="utf-8")
        journal.write_text(entry, encoding="utf-8")
        index.write_text(index_old.rstrip() + "\n* [" + str(meta["title"]) + "](" + journal.name + ")\n", encoding="utf-8")
        git("add", "--", record, str(journal.relative_to(ROOT)), str(index.relative_to(ROOT)))
        git("commit", "-m", "knowledge: " + summary[:70], "--", record, str(journal.relative_to(ROOT)), str(index.relative_to(ROOT)))
    except Exception:
        # Do not silently overwrite a partially committed update.
        raise
    return {"status": "committed", "head": git("rev-parse", "HEAD"), "journal": str(journal.relative_to(ROOT)), "record": record}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request", help="JSON file with record, expected_head, content, summary, actor, idempotency_key")
    args = parser.parse_args()
    print(json.dumps(publish(json.loads(Path(args.request).read_text(encoding="utf-8")))))


if __name__ == "__main__":
    main()
