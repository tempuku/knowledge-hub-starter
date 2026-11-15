"""Immutable Git-tree source loader for the native v1 projection (#31).

Source blobs are read from a resolved commit only. The same parser accepts raw
record/log blobs from a hash-pinned bundle, so no-Git builds use identical
validation and derived read models.
"""
from __future__ import annotations

import re
import posixpath
import subprocess
import sys
from pathlib import Path

from deterministic import ProjectionError

MARKDOWN_LINK = re.compile(r"(?P<prefix>!?\[[^\]\n]*\]\()(?P<target>[^)\s]+)(?P<suffix>\))")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _v1_record_candidate(raw: bytes) -> bool:
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    if raw.startswith(b"---\r\n"):
        raw = raw.replace(b"\r\n", b"\n")
    if not raw.startswith(b"---\n"):
        return False
    closing = raw.find(b"\n---\n", 4)
    header = raw[4:closing] if closing >= 0 else raw[4:]
    return bool(re.search(rb"(?m)^(?:schema_version|id)\s*:", header))


def _v1_log_candidate(raw: bytes) -> bool:
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.startswith(b"# Record history")


def _record_links(body: str, metadata: dict, source_path: str) -> list[dict]:
    """Extract canonical and relative current-record references from Markdown."""
    links = []
    in_fence = False
    fence_char = None
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[0]
            if not in_fence:
                in_fence, fence_char = True, marker
            elif marker == fence_char:
                in_fence, fence_char = False, None
            continue
        if in_fence:
            continue
        for match in MARKDOWN_LINK.finditer(line):
            if match.group("prefix").startswith("!"):
                continue
            target = match.group("target")
            label = match.group("prefix")[1:-2]
            if target.startswith("record:"):
                identifier, separator, fragment = target[7:].partition("#")
                identifier = identifier.lower()
                if not UUID.fullmatch(identifier) or (separator and not fragment):
                    raise ProjectionError("invalid canonical record link ID")
                links.append({"target_id": identifier, "fragment": fragment if separator else None,
                              "label": label, "available": True, "href": target})
            elif target.startswith(("http://", "https://", "mailto:")):
                continue
            elif re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                raise ProjectionError("unsupported Markdown link scheme")
            else:
                if target.startswith("#"):
                    target_path, fragment = source_path, target[1:]
                else:
                    target_path, _, fragment = target.partition("#")
                    if target_path.startswith("/") or "\\" in target_path or "%" in target_path or "?" in target_path:
                        raise ProjectionError("unsafe relative Markdown link")
                    target_path = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), target_path))
                if target_path != "openwiki" and not target_path.startswith("openwiki/"):
                    raise ProjectionError("relative Markdown link escapes openwiki")
                if target_path.endswith("/index.md") or target_path == "openwiki/index.md":
                    continue
                if not target_path.endswith(".md") or ("#" in target and not fragment):
                    raise ProjectionError("invalid relative record link")
                links.append({"target_path": target_path, "fragment": fragment or None,
                              "label": label, "available": True, "href": target})
    for source in metadata.get("sources", []):
        resource = source.get("resource", "") if isinstance(source, dict) else ""
        if resource.startswith("record:"):
            links.append({"target_id": resource[7:], "fragment": None,
                          "label": source.get("title", ""), "available": True, "href": resource})
    return links


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if result.returncode:
        raise ProjectionError("Git source failure: " + result.stderr.decode("utf-8", "replace"))
    return result.stdout


def _git_tree_entries(root: Path, commit: str) -> dict[str, tuple[str, str, str]]:
    raw = git(root, "ls-tree", "-r", "-z", "--full-tree", commit)
    entries = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, sep, path_bytes = item.partition(b"\t")
        fields = header.split(b" ")
        if not sep or len(fields) != 3:
            raise ProjectionError("malformed Git tree entry")
        try:
            mode, kind, oid = (value.decode("ascii") for value in fields)
            path = path_bytes.decode("utf-8", "strict")
        except UnicodeError as exc:
            raise ProjectionError("unsupported Git tree path") from exc
        if path in entries:
            raise ProjectionError("duplicate Git tree path")
        entries[path] = (mode, kind, oid)
    return entries


def parse_source_blobs(record_blobs: dict[str, bytes], log_blobs: dict[str, bytes]):
    """Validate exact source bytes and derive all in-memory projection inputs."""
    tools_dir = Path(__file__).resolve().parents[1] / "records"
    sys.path.insert(0, str(tools_dir))
    import validate_v1 as validator

    if set(log_blobs) != {path[:-3] + ".log.md" for path in record_blobs}:
        raise ProjectionError("record/log source set mismatch")
    records, histories, summaries = [], {}, {}
    seen_ids = set()
    project_refs = {}
    for path in sorted(record_blobs):
        raw = record_blobs[path]
        if not path.startswith("openwiki/") or not path.endswith(".md"):
            raise ProjectionError("unsafe canonical record path")
        log_path = path[:-3] + ".log.md"
        try:
            meta, canonical = validator.parse_record(raw, path)
            events = validator.parse_log(log_blobs[log_path], log_path)
            validator.validate_chain(events, path, meta, canonical, seen_ids)
        except (ValueError, UnicodeError) as exc:
            raise ProjectionError(f"invalid source record or history: {path}") from exc
        rid = meta["id"]
        if rid in histories:
            raise ProjectionError("duplicate canonical record ID")
        histories[rid] = events
        _, body = validator.frontmatter(canonical)
        record = {"id": rid, "title": meta["title"], "description": meta.get("description", ""),
                  "type": meta["type"], "status": meta["status"],
                  "project_id": meta.get("project_id"), "tags": meta.get("tags", []),
                  "area": path[len("openwiki/"):].rsplit("/", 1)[0],
                  "updated_at": events[-1]["recorded_at"], "version": len(events),
                  "content_bytes": len(raw), "content": canonical, "body": body, "path": path,
                  "links": _record_links(body, meta, path), "reminders": meta.get("reminders", [])}
        records.append(record)
        if record["project_id"] is not None:
            project_refs[rid] = record["project_id"]
        for event in events:
            after_meta, _ = validator.frontmatter(event["after"])
            summaries[event["id"]] = {
                "id": event["id"], "record_id": rid, "operation_id": event["operation_id"],
                "sequence": event["sequence"], "action": event["action"],
                "recorded_at": event["recorded_at"], "occurred_on": event["occurred_on"],
                "occurred_at": event["occurred_at"], "summary": event["summary"],
                "title": after_meta.get("title", "Unknown"),
                "status": after_meta.get("status", "Unknown"),
                "project_id": after_meta.get("project_id"),
                "tags": after_meta.get("tags", []),
                "actor_label": event["actor"]["label"],
                "provenance_kind": event["provenance"]["kind"],
                "type": after_meta.get("type", "Unknown"),
                "area": event["path_after"][len("openwiki/"):].rsplit("/", 1)[0]}
    record_ids = {record["id"] for record in records}
    project_ids = {record["id"] for record in records if record["type"] == "project"}
    if any(project_id not in project_ids for project_id in project_refs.values()):
        raise ProjectionError("project_id does not resolve to a project record")
    record_by_path = {record["path"]: record for record in records}
    bodies_by_path = {record["path"]: record["body"] for record in records}
    title_by_id = {record["id"]: record["title"] for record in records}
    for record in records:
        normalized_links = []
        for link in record["links"]:
            if "target_path" in link:
                target = record_by_path.get(link.pop("target_path"))
                if target is None:
                    raise ProjectionError("unresolved relative record link")
                link["target_id"] = target["id"]
                if link["fragment"] and link["fragment"] not in _heading_fragments(bodies_by_path[target["path"]]):
                    raise ProjectionError("unresolved relative record heading")
            if link["target_id"] not in record_ids:
                raise ProjectionError("unresolved canonical record link")
            if not link["label"]:
                link["label"] = title_by_id[link["target_id"]]
            normalized_links.append(link)
        record["links"] = normalized_links
    return records, histories, summaries


def _heading_fragments(markdown: str) -> set[str]:
    """Use the W-03 heading slug rule for path-based link fragments."""
    tools_dir = Path(__file__).resolve().parents[1] / "records"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from links_v1 import heading_fragments
    return heading_fragments(markdown)


def derive_aliases(records: list[dict], histories: dict[str, list[dict]]) -> dict:
    """Derive old-path and legacy-source aliases only from supplied source events."""
    by_path = {}
    entries = {}
    for record in records:
        rid = record["id"]
        for event in histories.get(rid, []):
            old_path = event.get("path_before")
            if old_path is not None and old_path != event.get("path_after"):
                by_path.setdefault(old_path, set()).add(rid)
            provenance = event.get("provenance", {})
            source_ref = provenance.get("source_ref")
            if provenance.get("kind") != "native" and source_ref:
                previous = entries.get(source_ref)
                if previous is not None and previous != event["id"]:
                    raise ProjectionError("ambiguous legacy entry alias")
                entries[source_ref] = event["id"]
    return {"paths": {path: sorted(ids) for path, ids in sorted(by_path.items())},
            "entries": dict(sorted(entries.items()))}


def load_revision(root: Path, revision: str):
    """Return (commit, tree, records, histories, summaries) from immutable Git."""
    source_root = Path(root).resolve()
    commit = git(source_root, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    tree = git(source_root, "rev-parse", commit + "^{tree}").decode().strip()
    tree_entries = _git_tree_entries(source_root, commit)
    paths = sorted(path for path in tree_entries if path.startswith("openwiki/"))
    record_blobs, log_blobs = {}, {}
    native_logs = set()
    for path in paths:
        mode, kind, _ = tree_entries[path]
        if path.endswith(".md") and (kind != "blob" or mode != "100644"):
            raise ProjectionError("openwiki Markdown sources must be regular non-executable blobs")
        if path.endswith(".log.md") and (kind != "blob" or mode != "100644"):
            raise ProjectionError("openwiki history logs must be regular non-executable blobs")
        if path.endswith(".log.md") and kind == "blob":
            raw = git(source_root, "show", f"{commit}:{path}")
            if _v1_log_candidate(raw):
                native_logs.add(path)
    for path in sorted(filter(None, paths)):
        if not path.endswith(".md") or path.endswith(".log.md") or path.rsplit("/", 1)[-1] in ("index.md", "log.md"):
            continue
        mode, kind, _ = tree_entries[path]
        if kind != "blob":
            continue
        raw = git(source_root, "show", f"{commit}:{path}")
        if not _v1_record_candidate(raw):
            continue  # v0 legacy records are migration input, not v1 export sources.
        log_path = path[:-3] + ".log.md"
        log_entry = tree_entries.get(log_path)
        if log_entry is None or log_entry[0] != "100644" or log_entry[1] != "blob":
            raise ProjectionError("canonical record has no regular sibling history")
        record_blobs[path] = raw
        log_blobs[log_path] = git(source_root, "show", f"{commit}:{log_path}")
        native_logs.discard(log_path)
    if native_logs:
        raise ProjectionError("orphan native history log: " + sorted(native_logs)[0])
    records, histories, summaries = parse_source_blobs(record_blobs, log_blobs)
    return commit, tree, records, histories, summaries


def load_bundle(bundle_path: Path, receipt_path: Path, expected_receipt_sha256: str):
    """Load raw source blobs from an externally pinned no-Git bundle."""
    from sourcebundle import load_bundle as verify_bundle

    commit, tree, manifest, blobs, receipt = verify_bundle(
        bundle_path, receipt_path, expected_receipt_sha256)
    record_blobs, log_blobs = {}, {}
    by_path = {entry["path"]: entry for entry in manifest}
    for path, entry in sorted(by_path.items()):
        if not path.startswith("openwiki/") or not path.endswith(".md") or path.endswith(".log.md") or path.rsplit("/", 1)[-1] in ("index.md", "log.md"):
            continue
        if entry["type"] != "blob":
            continue
        if entry["mode"] != "100644":
            raise ProjectionError("canonical record must be a regular non-executable blob")
        raw = blobs[entry["oid"]]
        if not _v1_record_candidate(raw):
            continue
        record_blobs[path] = raw
        log_path = path[:-3] + ".log.md"
        log_entry = by_path.get(log_path)
        if log_entry is None or log_entry["type"] != "blob" or log_entry["mode"] != "100644":
            raise ProjectionError("canonical source has no sibling history in bundle")
        log_blobs[log_path] = blobs[log_entry["oid"]]
    expected_native_logs = {path for path, entry in by_path.items()
                            if path.startswith("openwiki/") and path.endswith(".log.md") and
                            entry["type"] == "blob" and _v1_log_candidate(blobs[entry["oid"]])}
    expected_native_logs -= set(log_blobs)
    if expected_native_logs:
        raise ProjectionError("orphan native history log: " + sorted(expected_native_logs)[0])
    if any(path.startswith("openwiki/") and path.endswith(".md") and entry["mode"] != "100644"
           for path, entry in by_path.items()):
        raise ProjectionError("openwiki Markdown sources must be regular non-executable blobs")
    if any(path.startswith("openwiki/") and path.endswith(".log.md") and
           (entry["type"] != "blob" or entry["mode"] != "100644")
           for path, entry in by_path.items()):
        raise ProjectionError("openwiki history logs must be regular non-executable blobs")
    records, histories, summaries = parse_source_blobs(record_blobs, log_blobs)
    policy_entry = by_path.get("config/publication.json")
    policy_bytes = blobs[policy_entry["oid"]] if policy_entry and policy_entry["type"] == "blob" else None
    return commit, tree, records, histories, summaries, policy_bytes, receipt
