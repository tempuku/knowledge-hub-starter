#!/usr/bin/env python3
"""Evidence-only audit of frozen legacy source metadata and native event histories.

Does not classify dispositions, allocate IDs, or approve publication.
Usage: python3 scripts/audit_legacy_evidence.py --revision <full-sha> --output migration/evidence-v1.json
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVENT = re.compile(rb"```json\r?\n(.*?)\r?\n```", re.S)
LINK = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")

def git_bytes(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])

def audit(revision):
    paths = sorted(p for p in git_bytes("ls-tree", "-r", "--name-only", "-z", revision, "--", "openwiki").decode().split("\0") if p.endswith(".md"))
    result = []
    for path in paths:
        if pathlib.PurePosixPath(path).name == "index.md":
            continue
        raw = git_bytes("show", revision + ":" + path)
        text = raw.decode("utf-8", errors="replace")
        frontmatter = {}
        if text.startswith("---\n") and "\n---\n" in text[4:]:
            header = text.split("\n---\n", 1)[0][4:]
            for line in header.splitlines():
                match = re.match(r"^([A-Za-z_][A-Za-z_0-9-]*):\s*(.*)$", line)
                if match:
                    frontmatter[match.group(1)] = match.group(2).strip().strip("'\"")
        is_log = path.endswith(".log.md") or pathlib.PurePosixPath(path).name == "log.md"
        entries = []
        failures = []
        if is_log and path.endswith(".log.md"):
            for i, match in enumerate(EVENT.finditer(raw)):
                try:
                    event = json.loads(match.group(1))
                    if not isinstance(event, dict):
                        raise ValueError("not an object")
                    entries.append({
                        "ordinal": i + 1,
                        "id": event.get("event_id", event.get("id")),
                        "timestamp": event.get("recorded_at", event.get("timestamp", event.get("occurred_at"))),
                        "actor": event.get("actor"),
                        "summary": event.get("summary"),
                        "before_sha256": hashlib.sha256(event["before"].encode()).hexdigest() if isinstance(event.get("before"), str) else None,
                        "after_sha256": hashlib.sha256(event["after"].encode()).hexdigest() if isinstance(event.get("after"), str) else None,
                    })
                except (ValueError, TypeError, UnicodeError) as exc:
                    failures.append(f"event {i + 1}: {exc}")
        sibling = path[:-7] + ".md" if path.endswith(".log.md") else path[:-3] + ".log.md"
        result.append({
            "path": path,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "is_log": is_log,
            "sibling_path": sibling if sibling in paths else None,
            "frontmatter": frontmatter,
            "relative_links": sorted(set(link for link in LINK.findall(text) if not re.match(r"^(?:[a-z]+:|/|#)", link, re.I))),
            "native_events": entries,
            "event_parse_errors": failures,
            "review_status": "pending",
        })
    return {"schema_version": 1, "base_revision": revision, "publication_approved": False, "items": result}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", default="migration/evidence-v1.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = audit(args.revision)
    output = ROOT / args.output
    serialized = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != serialized:
            parser.error("evidence is missing/stale; regenerate from frozen revision")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    print(f"{len(data['items'])} non-index Markdown sources audited; publication NOT approved")

if __name__ == "__main__":
    main()
