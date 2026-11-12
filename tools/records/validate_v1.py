#!/usr/bin/env python3
"""Fail-closed validator for Knowledge Hub v1 canonical records and sibling history.

No migration or file repair is performed. Existing v0.2 sources remain untouched.
Use --base <trusted-commit> in CI to check append-only history against Git.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import yaml

AREAS = {"projects", "ideas", "notes", "concepts", "adr", "design"}
STATUSES = {"draft", "stable", "completed", "deprecated"}
ACTIONS = {"CREATED", "UPDATED", "MOVED", "ARCHIVED", "REOPENED", "IMPORTED"}
PROVENANCE = {"native", "legacy-log", "legacy-journal", "git-backfill"}
WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {"com" + str(i) for i in range(1, 10)} | {"lpt" + str(i) for i in range(1, 10)}
KEBAB = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})\Z")
ENTRY = re.compile(r"## Entry ([0-9a-f-]{36})\n```json\n")
EVENT_KEYS = {
    "schema_version", "id", "record_id", "operation_id", "sequence", "action",
    "recorded_at", "occurred_on", "occurred_at", "actor", "summary",
    "path_before", "path_after", "before", "after", "before_sha256",
    "after_sha256", "previous_event_id", "idempotency_key", "request_sha256",
    "provenance",
}
META_KEYS = {
    "id", "schema_version", "type", "title", "description", "status",
    "visibility", "project_id", "tags", "occurred_on", "occurred_at",
    "reminders", "sources",
}


class IntegrityError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def exact_keys(value, keys, label):
    require(type(value) is dict and set(value) == set(keys),
            f"{label}: expected exactly {sorted(keys)}")


def uid(value, label):
    require(type(value) is str and bool(re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", value)),
        f"{label}: invalid lowercase UUIDv4")
    require(str(uuid.UUID(value)) == value, f"{label}: invalid canonical UUIDv4")
    return value


def digest(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def one_line(value, label, minimum, maximum):
    require(type(value) is str and value == value.strip() and
            minimum <= len(value) <= maximum and
            not any(c in value for c in ("\r", "\n", "\0")),
            f"{label}: invalid length, whitespace or newline")


def date_or_time(value, label, allow_date=True):
    require(type(value) is str, f"{label}: must be quoted string")
    if allow_date and DATE.fullmatch(value):
        try:
            dt.date.fromisoformat(value)
        except ValueError as exc:
            raise IntegrityError(f"{label}: invalid Gregorian date") from exc
        return "date"
    require(bool(TIME.fullmatch(value)), f"{label}: offset-qualified second-precision time required")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.utcoffset() is not None, f"{label}: missing offset")
    except ValueError as exc:
        raise IntegrityError(f"{label}: invalid timestamp or offset") from exc
    return "time"


def occurrence(day, instant, label):
    if day is not None:
        require(date_or_time(day, label + ".occurred_on") == "date", f"{label}: invalid occurrence date")
    if instant is not None:
        require(date_or_time(instant, label + ".occurred_at", False) == "time",
                f"{label}: invalid occurrence time")
        require(day == instant[:10], f"{label}: occurred_on must equal written timestamp date")


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        require(isinstance(node, yaml.MappingNode), "frontmatter: mapping required")
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            require(type(key) is str, "frontmatter: non-string YAML key")
            require(key not in result, f"frontmatter: duplicate key {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def frontmatter(source):
    require(source.startswith("---\n"), "record: frontmatter must start with ---")
    end = source.find("\n---\n", 4)
    require(end >= 0, "record: missing closing YAML delimiter")
    head, body = source[4:end], source[end + 5:]
    require("\ufeff" not in source[:1] and "\r" not in source and "\0" not in source,
            "record: BOM, CR or NUL")
    require(source.endswith("\n") and not source.endswith("\n\n"),
            "record: must end in one LF")
    try:
        events = list(yaml.parse(head, Loader=UniqueLoader))
        require(not any(isinstance(e, yaml.AliasEvent) or getattr(e, "anchor", None)
                        for e in events), "frontmatter: YAML aliases and anchors forbidden")
        metadata = yaml.load(head, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise IntegrityError(f"frontmatter: invalid YAML: {exc}") from exc
    require(type(metadata) is dict, "frontmatter: must contain a mapping")
    return metadata, body


def safe_path(value, label, kind="record"):
    require(type(value) is str and value.startswith("openwiki/") and
            "\\" not in value and "\0" not in value and
            not any(ord(c) < 32 or ord(c) == 127 for c in value) and
            len(value.encode("utf-8")) <= 240, f"{label}: unsafe path")
    parts = value.split("/")
    require(len(parts) >= 3 and parts[1] in AREAS and len(parts[1:-1]) <= 8,
            f"{label}: invalid area or depth")
    require(all(KEBAB.fullmatch(seg) and seg not in WINDOWS_RESERVED for seg in parts[1:-1]),
            f"{label}: unsafe directory segment")
    suffix = ".log.md" if kind == "log" else ".md"
    require(parts[-1].endswith(suffix), f"{label}: invalid extension")
    slug = parts[-1][:-len(suffix)]
    require(KEBAB.fullmatch(slug) and slug not in {"index", "log"} | WINDOWS_RESERVED,
            f"{label}: reserved or invalid slug")
    return value


def validate_meta(meta, body, label):
    require(set(meta) >= {"id", "schema_version", "type", "title", "status", "visibility"},
            f"{label}: missing required frontmatter")
    require(all(k in META_KEYS or k.startswith("x_") for k in meta),
            f"{label}: unknown unprefixed key")
    uid(meta["id"], label + ".id")
    require(type(meta["schema_version"]) is int and meta["schema_version"] == 1,
            f"{label}: schema_version must be integer 1")
    one_line(meta["type"], label + ".type", 1, 64)
    require(KEBAB.fullmatch(meta["type"]), f"{label}: type must be kebab-case")
    one_line(meta["title"], label + ".title", 1, 200)
    require(type(meta["status"]) is str and meta["status"] in STATUSES, f"{label}: invalid status")
    require(type(meta["visibility"]) is str and meta["visibility"] in {"private", "public"}, f"{label}: invalid visibility")
    if "description" in meta:
        one_line(meta["description"], label + ".description", 0, 500)
    if "project_id" in meta:
        uid(meta["project_id"], label + ".project_id")
        require(meta["type"] != "project", f"{label}: project cannot reference another project")
    tags = meta.get("tags", [])
    require(type(tags) is list and len(tags) <= 32, f"{label}: invalid tags")
    require(all(type(x) is str and len(x) <= 64 and KEBAB.fullmatch(x) for x in tags)
            and len(tags) == len(set(tags)), f"{label}: duplicate or invalid tags")
    occurrence(meta.get("occurred_on"), meta.get("occurred_at"), label)
    reminders = meta.get("reminders", [])
    require(type(reminders) is list and len(reminders) <= 100, f"{label}: invalid reminders")
    seen = set()
    for idx, item in enumerate(reminders):
        require(type(item) is list and len(item) == 2, f"{label}: reminder {idx} must be tuple")
        when, note = item
        one_line(note, f"{label}: reminder {idx} text", 1, 240)
        if type(when) is list:
            require(len(when) == 2, f"{label}: invalid reminder range")
            a, b = when
            kind = date_or_time(a, f"{label}: start")
            require(kind == date_or_time(b, f"{label}: end"),
                    f"{label}: range cannot mix dates and times")
            if kind == "time":
                require(a[-6:] == b[-6:], f"{label}: range offsets must match")
                require(dt.datetime.fromisoformat(a.replace("Z","+00:00")) <=
                        dt.datetime.fromisoformat(b.replace("Z","+00:00")),
                        f"{label}: reversed range")
            else:
                require(a <= b, f"{label}: reversed date range")
        else:
            date_or_time(when, f"{label}: reminder date")
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        require(key not in seen, f"{label}: duplicate reminder")
        seen.add(key)
    sources = meta.get("sources", [])
    require(type(sources) is list, f"{label}: sources must be list")
    for item in sources:
        require(type(item) is dict and set(item) in ({"resource"}, {"resource", "title"}),
                f"{label}: invalid source mapping")
        resource = item["resource"]
        require(type(resource) is str, f"{label}: invalid source resource")
        if resource.startswith("record:"):
            uid(resource[7:], label + ".source.record")
        else:
            u = urlsplit(resource)
            require(u.scheme in {"http", "https"} and bool(u.netloc) and
                    not any(c in resource for c in "\r\n\0"),
                    f"{label}: invalid URL source")
        if "title" in item:
            one_line(item["title"], label + ".source.title", 1, 200)
    for key in meta:
        if key.startswith("x_"):
            try:
                json.dumps(meta[key], allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise IntegrityError(f"{label}: extension must be JSON-compatible") from exc
    require(body.strip() != "" or meta["type"] == "project",
            f"{label}: only project may have empty body")
    return meta


def parse_record(raw, path):
    require(len(raw) <= 1048576, f"{path}: record exceeds 1 MiB")
    try:
        value = raw.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise IntegrityError(f"{path}: invalid UTF-8") from exc
    meta, body = frontmatter(value)
    return validate_meta(meta, body, path), value


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, f"log: duplicate JSON key {key}")
        out[key] = value
    return out


def forbid_float(value):
    raise IntegrityError("log: JSON floats are forbidden")


def parse_log(raw, path):
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise IntegrityError(f"{path}: log must be UTF-8") from exc
    require(text.startswith("# Record history\n\n") and
            "\r" not in text and "\0" not in text and not text.startswith("\ufeff"),
            f"{path}: invalid v1 log header")
    pos = len("# Record history\n\n")
    events = []
    while pos < len(text):
        match = ENTRY.match(text, pos)
        require(match is not None, f"{path}: malformed section or stray text at {pos}")
        end = text.find("\n```\n", match.end())
        require(end != -1, f"{path}: unterminated fenced JSON")
        source = text[match.end():end]
        try:
            event = json.loads(source, object_pairs_hook=unique_pairs, parse_float=forbid_float,
                               parse_constant=forbid_float)
        except json.JSONDecodeError as exc:
            raise IntegrityError(f"{path}: invalid JSON: {exc}") from exc
        require(type(event) is dict, f"{path}: event must be object")
        require(event.get("id") == match.group(1), f"{path}: event heading mismatch")
        require(source == json.dumps(event, ensure_ascii=False, indent=2),
                f"{path}: JSON must use canonical two-space serialization")
        events.append(event)
        pos = end + len("\n```\n")
        if pos < len(text):
            require(text[pos] == "\n", f"{path}: expected blank line between events")
            pos += 1
    require(bool(events), f"{path}: empty history log")
    return events


def validate_event(e, label):
    exact_keys(e, EVENT_KEYS, label)
    require(type(e["schema_version"]) is int and e["schema_version"] == 1,
            f"{label}: invalid version")
    for name in ("id", "record_id", "operation_id", "idempotency_key"):
        uid(e[name], f"{label}.{name}")
    require(type(e["sequence"]) is int and e["sequence"] > 0,
            f"{label}: invalid sequence")
    require(type(e["action"]) is str and e["action"] in ACTIONS, f"{label}: invalid action")
    require(type(e["recorded_at"]) is str and
            e["recorded_at"].endswith("Z") and TIME.fullmatch(e["recorded_at"]),
            f"{label}: recorded_at must be UTC second-precision Z")
    date_or_time(e["recorded_at"], label + ".recorded_at", False)
    occurrence(e["occurred_on"], e["occurred_at"], label)
    exact_keys(e["actor"], {"id", "kind", "label"}, label + ".actor")
    one_line(e["actor"]["id"], label + ".actor.id", 1, 200)
    one_line(e["actor"]["label"], label + ".actor.label", 1, 100)
    require(type(e["actor"]["kind"]) is str and e["actor"]["kind"] in {"human", "agent", "migration"},
            f"{label}: invalid actor kind")
    one_line(e["summary"], label + ".summary", 1, 240)
    if e["path_before"] is not None:
        safe_path(e["path_before"], label + ".path_before")
    safe_path(e["path_after"], label + ".path_after")
    require(type(e["after"]) is str, f"{label}: missing after snapshot")
    require(e["after_sha256"] == digest(e["after"]), f"{label}: after hash mismatch")
    require((e["before"] is None) == (e["before_sha256"] is None),
            f"{label}: before/hash null mismatch")
    if e["before"] is not None:
        require(type(e["before"]) is str and e["before_sha256"] == digest(e["before"]),
                f"{label}: before hash mismatch")
    require(type(e["request_sha256"]) is str and SHA.fullmatch(e["request_sha256"]),
            f"{label}: invalid request digest")
    exact_keys(e["provenance"], {"kind", "source_ref", "original_time"}, label + ".provenance")
    p = e["provenance"]
    require(type(p["kind"]) is str and p["kind"] in PROVENANCE, f"{label}: invalid provenance")
    require(p["source_ref"] is None or type(p["source_ref"]) is str,
            f"{label}: invalid provenance ref")
    require(p["original_time"] is None or type(p["original_time"]) is str,
            f"{label}: invalid provenance time")
    if p["kind"] == "native":
        require(p["source_ref"] is None and p["original_time"] is None,
                f"{label}: native provenance must be empty")
    if e["action"] == "IMPORTED":
        require(p["kind"] != "native" and e["actor"]["kind"] == "migration",
                f"{label}: IMPORTED is migration-only")
    if p["kind"] == "native":
        # A migration wrapper may preserve legacy snapshots, but a native write cannot.
        if e["before"] is not None:
            validate_meta(*frontmatter(e["before"]), label + ".before")
        validate_meta(*frontmatter(e["after"]), label + ".after")


def validate_chain(events, path, meta, content, seen_events):
    prior = None
    for i, e in enumerate(events, 1):
        label = f"{path}: entry {i}"
        validate_event(e, label)
        require(e["record_id"] == meta["id"], f"{label}: wrong record ID")
        require(e["sequence"] == i, f"{label}: broken sequence")
        require(e["id"] not in seen_events, f"{label}: globally duplicated event ID")
        seen_events.add(e["id"])
        if i == 1:
            require(e["before"] is None and e["before_sha256"] is None and
                    e["path_before"] is None and e["previous_event_id"] is None,
                    f"{label}: first event must start empty")
            require(e["action"] in {"CREATED", "IMPORTED"},
                    f"{label}: first event must be CREATED/IMPORTED")
        else:
            require(e["action"] != "CREATED", f"{label}: CREATED may only be first")
            require(e["previous_event_id"] == prior["id"] and
                    e["before"] == prior["after"] and
                    e["path_before"] == prior["path_after"],
                    f"{label}: broken previous event/snapshot/path chain")
            require(e["recorded_at"] >= prior["recorded_at"],
                    f"{label}: nonmonotonic recorded time")
        prior = e
    require(prior["path_after"] == path and prior["after"] == content,
            f"{path}: final log snapshot/path differs from canonical record")


def git(root, *args, missing_ok=False):
    p = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if p.returncode:
        if missing_ok:
            return None
        raise IntegrityError(f"git {' '.join(args)}: {p.stderr.decode(errors='replace').strip()}")
    return p.stdout


def repository(root, base=None, strict_indexes=False):
    index = git(root, "ls-files", "--cached", "-z", "--stage").split(b"\0")
    tracked, links = {}, set()
    for entry in filter(None, index):
        try:
            header, path = entry.split(b"\t", 1)
            mode = header.split(b" ")[0]
            name = path.decode("utf-8", "strict")
        except (UnicodeError, ValueError) as exc:
            raise IntegrityError("git index contains invalid path") from exc
        tracked[name] = True
        if mode == b"120000":
            links.add(name)
    checks = set()
    for p in tracked:
        if not p.startswith("openwiki/"):
            continue
        low = p.casefold()
        require(low not in checks, f"{p}: case-insensitive path collision")
        checks.add(low)
        parts = p.split("/")
        require(not any("/".join(parts[:i]) in links for i in range(1, len(parts)+1)),
                f"{p}: symlink at a path component")
    records, paths, event_ids = {}, {}, set()
    for path in sorted(tracked):
        if not path.startswith("openwiki/") or not path.endswith(".md") or path.endswith(".log.md"):
            continue
        if path.rsplit("/", 1)[-1] in {"index.md", "log.md"} or path in {"openwiki/GUIDE.md", "openwiki/CI.md"}:
            continue
        blob = git(root, "show", ":" + path)
        # Legacy input is NOT a v1 record. New legacy authoring is forbidden below.
        header = blob[:4096].split(b"\n---\n", 1)[0] if blob.startswith(b"---\n") else b""
        if not re.search(rb"(?m)^(?:schema_version|id)\s*:", header):
            continue
        safe_path(path, path)
        meta, content = parse_record(blob, path)
        log_path = path[:-3] + ".log.md"
        safe_path(log_path, log_path, "log")
        require(log_path in tracked, f"{path}: missing sibling log")
        events = parse_log(git(root, "show", ":" + log_path), log_path)
        require(meta["id"] not in records, f"{path}: duplicate global record ID")
        records[meta["id"]] = meta
        paths[path] = (meta, events)
        validate_chain(events, path, meta, content, event_ids)
    for path in tracked:
        if path.endswith(".log.md") and path not in {p[:-3]+".log.md" for p in paths}:
            # Legacy logs are explicitly retained until migration; v1 header identifies
            # an orphan v1 log, even if its companion record disappeared.
            if git(root, "show", ":" + path).startswith(b"# Record history\n"):
                raise IntegrityError(f"{path}: orphan v1 sibling log")
    for record_id, meta in records.items():
        project = meta.get("project_id")
        if project is not None:
            require(type(project) is str and project in records and records[project]["type"] == "project",
                    f"{record_id}: unresolved/non-project project_id")
    require(not (set(records) & event_ids), "record UUID collides with an event UUID")
    if base:
        compare_base(root, base, tracked, paths)
    if strict_indexes:
        verify_indexes(root, tracked)
    return {"records": len(paths), "events": len(event_ids)}


def compare_base(root, base, tracked, paths):
    # Required for PR CI. This is a trusted Git base, never inferred from a
    # submitted record or an event-provided digest.
    git(root, "rev-parse", "--verify", base + "^{commit}")
    changes = git(root, "diff", "--name-status", "--no-renames", base, "--", "openwiki").decode()
    for line in changes.splitlines():
        kind, *names = line.split("\t")
        path = names[-1]
        if not path.endswith(".md") or path.endswith(".log.md") or path.rsplit("/",1)[-1] in {"index.md","log.md"} or path in {"openwiki/GUIDE.md","openwiki/CI.md"}:
            continue
        if kind.startswith("A"):
            require(path in paths, f"{path}: new record must use v1 schema and sibling log")
    for path, (_, events) in paths.items():
        log_path = path[:-3] + ".log.md"
        initial = events[0]["path_after"][:-3] + ".log.md"
        # History files move, but their original first path is immutable.
        old = git(root, "show", base + ":" + initial, missing_ok=True)
        if old is None:
            continue
        current = git(root, "show", ":" + log_path)
        require(current.startswith(old) and
                (len(current) == len(old) or current[len(old):].startswith(b"\n")),
                f"{log_path}: trusted-base history prefix rewritten")
        old_record = git(root, "show", base + ":" + path, missing_ok=True)
        if old_record is not None and old_record != git(root, "show", ":" + path):
            require(len(current) > len(old), f"{path}: direct record edit without appended event")


def verify_indexes(root, tracked):
    # Used on isolated v1 fixtures now; required for full tree after migration.
    expected = {}
    for p in tracked:
        if not p.startswith("openwiki/") or not p.endswith(".md") or p.endswith(".log.md"):
            continue
        if p.rsplit("/",1)[-1] not in {"index.md","log.md"}:
            folder = p.rsplit("/", 1)[0]
            expected.setdefault(folder, set()).add(p.rsplit("/", 1)[1])
        parent = p.rsplit("/", 1)[0]
        while parent != "openwiki":
            holder, child = parent.rsplit("/", 1)
            expected.setdefault(holder, set()).add(child + "/")
            parent = holder
    for folder, entries in expected.items():
        idx = folder + "/index.md"
        require(idx in tracked, f"{idx}: missing structural index")
        text = git(root, "show", ":" + idx).decode("utf-8", "strict")
        links = re.findall(r"^[*-] \[[^\]]+\]\(([^)]+)\)\s*$", text, re.M)
        require(links == sorted(entries), f"{idx}: indexes must list each direct child exactly once in sorted path order")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--base", help="trusted Git base commit for append-only CI check")
    parser.add_argument("--strict-indexes", action="store_true", help="require complete sorted v1 indexes")
    args = parser.parse_args()
    try:
        result = repository(args.root, args.base, args.strict_indexes)
    except (IntegrityError, UnicodeError, OSError, ValueError) as exc:
        print(f"v1 integrity: FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"v1 integrity: OK: {result['records']} v1 records and {result['events']} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
