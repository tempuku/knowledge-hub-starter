#!/usr/bin/env python3
"""Trusted OKF record writer: create/update record plus append-only self-contained log."""
import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
ENTRY = re.compile(r"^## Entry ([a-z0-9-]+)\n\x60\x60\x60json\n(.*?)\n\x60\x60\x60(?:\n|$)", re.M | re.S)


def entries(text):
    result = []
    for match in ENTRY.finditer(text):
        data = json.loads(match.group(2))
        if data.get("id") != match.group(1):
            raise ValueError("Log entry ID mismatch")
        result.append(data)
    if text.count("## Entry ") != len(result):
        raise ValueError("Malformed log entry")
    return result


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def publish(request):
    relative = request["record"]
    path = (ROOT / relative).resolve()
    base = (ROOT / "openwiki").resolve()
    if not path.is_relative_to(base) or path.suffix != ".md" or path.is_symlink() or path.name.endswith(".log.md"):
        raise ValueError("Unsafe record path")
    log = path.with_name(path.stem + ".log.md")
    if log.is_symlink():
        raise ValueError("Unsafe log path")
    if git("status", "--porcelain"):
        raise ValueError("Working tree must be clean")
    if request["expected_head"] != git("rev-parse", "HEAD"):
        raise ValueError("Stale expected_head")
    new = request["content"]
    match = FRONT.match(new)
    if not match:
        raise ValueError("Missing frontmatter")
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict) or not meta.get("title") or not meta.get("type"):
        raise ValueError("Invalid record metadata")
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == new:
        raise ValueError("No content change")
    actor = request["actor"].strip()
    summary = request["summary"].strip()
    entry_id = request["idempotency_key"]
    if not actor or "\n" in actor or not summary or len(summary) > 240 or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", entry_id):
        raise ValueError("Invalid actor, summary or idempotency key")
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    log_old = log.read_text(encoding="utf-8") if log.exists() else "# OKF Record Change Log\n\n"
    previous = entries(log_old)
    if any(e["id"] == entry_id for e in previous):
        raise ValueError("Duplicate entry ID")
    if old is None and previous:
        raise ValueError("Create cannot reuse existing log")
    if old is not None and not log.exists():
        raise ValueError("Existing record has no log; migrate it first")
    if previous and previous[-1]["after_sha256"] != sha(old):
        raise ValueError("Existing log does not match current record")
    entry = {
        "id": entry_id, "timestamp": timestamp, "actor": actor,
        "action": "CREATED" if old is None else "UPDATED",
        "summary": summary, "record": relative,
        "visibility": meta.get("visibility", "private"),
        "before": old, "after": new,
        "before_sha256": sha(old) if old is not None else None,
        "after_sha256": sha(new),
    }
    log_new = log_old.rstrip() + "\n\n## Entry " + entry_id + "\n\x60\x60\x60json\n" + json.dumps(entry, ensure_ascii=False, indent=2) + "\n\x60\x60\x60\n"
    # Commit both paths together; on failure restore files without touching other paths.
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(new, encoding="utf-8")
        log.write_text(log_new, encoding="utf-8")
        git("add", "--", relative, log.relative_to(ROOT).as_posix())
        git("commit", "-m", "knowledge: " + summary[:70], "--", relative, log.relative_to(ROOT).as_posix())
    except Exception:
        if old is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(old, encoding="utf-8")
        if log.exists():
            if log_old == "# OKF Record Change Log\n\n" and not previous:
                log.unlink()
            else:
                log.write_text(log_old, encoding="utf-8")
        subprocess.run(["git", "reset", "-q", "--", relative, log.relative_to(ROOT).as_posix()], cwd=ROOT)
        raise
    return {"status": "committed", "record": relative, "log": log.relative_to(ROOT).as_posix(), "entry_id": entry_id, "head": git("rev-parse", "HEAD")}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("request", help="JSON: record, content, summary, actor, idempotency_key, expected_head")
    args = p.parse_args()
    print(json.dumps(publish(json.loads(Path(args.request).read_text(encoding="utf-8")))))
