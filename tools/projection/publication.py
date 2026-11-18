"""Fail-closed publication allowlist validation for #32.

This module deliberately does not authorize a public build on its own.
The exporter must also enforce snapshot eligibility and audit output bytes.
"""
from __future__ import annotations

import hashlib
import json
import posixpath
import re
from pathlib import Path

from deterministic import ProjectionError, json_bytes

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
RECORD_REF = re.compile(r"record:([0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})(?:#[^\s)<>]+)?")
MARKDOWN_RECORD_LINK = re.compile(r"\[[^\]\n]*\]\(record:([0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})(?:#[^\s)<>]+)?(?:\s+['\"][^)]*['\"])?\)")
FIELDS = {"schema_version", "record_ids", "event_ids", "actor_labels"}
MARKDOWN_LINK = re.compile(r"(?P<prefix>!?\[[^\]\n]*\]\()(?P<target>[^)\s]+)(?P<suffix>\))")
EXTERNAL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def validate_policy(raw: bytes) -> tuple[dict, str]:
    """Reject unknown fields, duplicates, wildcards, malformed IDs and unsorted lists."""
    try:
        policy = json.loads(raw, object_pairs_hook=_unique_pairs)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise ProjectionError("invalid publication policy JSON") from exc
    if not isinstance(policy, dict) or set(policy) != FIELDS or type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        raise ProjectionError("unknown or incomplete publication policy schema")
    for field in ("record_ids", "event_ids", "actor_labels"):
        values = policy[field]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v or v.strip() != v for v in values):
            raise ProjectionError("invalid publication allowlist")
        if values != sorted(set(values)):
            raise ProjectionError("allowlist must be unique and sorted")
        if any("*" in v or "?" in v for v in values):
            raise ProjectionError("wildcards are prohibited")
    for field in ("record_ids", "event_ids"):
        if any(UUID.fullmatch(v) is None for v in policy[field]):
            raise ProjectionError("invalid UUID in publication allowlist")
    if any(len(v) > 128 or any(ord(c) < 32 for c in v) for v in policy["actor_labels"]):
        raise ProjectionError("invalid actor label")
    return policy, hashlib.sha256(json_bytes(policy)).hexdigest()


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def load_policy(root: Path, mode: str, *, revision_bytes: bytes | None = None):
    """A public policy must be supplied from the same immutable revision as source.

    No working-tree fallback: caller must load the versioned policy via git show.
    """
    if mode != "public":
        raise ProjectionError("public policy loader only accepts explicit public mode")
    if revision_bytes is None:
        raise ProjectionError("missing immutable public policy")
    return validate_policy(revision_bytes)


def _visibility(snapshot: str | None) -> str | None:
    if snapshot is None:
        return None
    # Reuse canonical frontmatter parsing, never infer visibility from body text.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "records"))
    from validate_v1 import frontmatter
    try:
        metadata, _ = frontmatter(snapshot)
    except (ValueError, TypeError) as exc:
        raise ProjectionError("invalid publication snapshot") from exc
    value = metadata.get("visibility")
    if value not in ("public", "private"):
        raise ProjectionError("missing or invalid snapshot visibility")
    return value


def select_public(records: list[dict], histories: dict[str, list[dict]],
                  summaries: dict[str, dict], policy: dict):
    """Select current public records and explicitly approved public-only events.

    Never pass a private-before transition to the diff generator. A public
    record with no approved history remains visible with an empty history.
    """
    allowed_records = set(policy["record_ids"])
    allowed_events = set(policy["event_ids"])
    allowed_labels = set(policy["actor_labels"])
    chosen_records, chosen_histories, chosen_summaries = [], {}, {}
    eligible_ids = {record["id"] for record in records
                    if record["id"] in allowed_records and _visibility(record["content"]) == "public"}
    hidden_paths = set()
    for candidate in records:
        if candidate["id"] in eligible_ids:
            continue
        if candidate.get("path"):
            hidden_paths.add(candidate["path"])
            hidden_paths.add(posixpath.basename(candidate["path"]))
        for hidden_event in histories.get(candidate["id"], []):
            old_path = hidden_event.get("path_before")
            if old_path:
                hidden_paths.add(old_path)
                hidden_paths.add(posixpath.basename(old_path))
    for record in records:
        rid = record["id"]
        if rid not in eligible_ids:
            continue
        public_record = dict(record)
        # A hidden destination has no usable public route. Rewrite its current
        # source link to plain text and clear its machine-readable identity.
        # Event snapshots are deliberately left exact and remain subject to
        # the byte audit; they are never rewritten into fabricated history.
        content = public_record.get("content")
        hidden_ids = {candidate["id"] for candidate in records} - eligible_ids
        if isinstance(content, str):
            hidden_ids.update(match.group(1) for match in RECORD_REF.finditer(content)
                              if match.group(1) not in eligible_ids)
        if isinstance(content, str):
            content = _rewrite_snapshot_markdown_links(
                content, public_record.get("links", []), eligible_ids,
                public_record.get("path", ""), hidden_paths)
            public_record["content"] = _rewrite_ineligible_record_refs(content, hidden_ids)
            public_record["content_bytes"] = len(public_record["content"].encode("utf-8"))
        if isinstance(public_record.get("body"), str):
            body = _rewrite_markdown_links(
                public_record["body"], public_record.get("links", []), eligible_ids,
                public_record.get("path", ""), hidden_paths)
            public_record["body"] = _rewrite_ineligible_record_refs(body, hidden_ids)
        if isinstance(public_record.get("links"), list):
            sanitized_links = []
            for link in public_record["links"]:
                link = dict(link)
                if link.get("target_id") not in eligible_ids:
                    link.update(target_id=None, fragment=None,
                                label="Unavailable in this view", available=False, href=None)
                else:
                    # Public Markdown is rewritten to canonical IDs. Never emit
                    # original source paths as renderer lookup keys.
                    link["href"] = "record:" + link["target_id"] + (
                        "#" + link["fragment"] if link.get("fragment") else "")
                sanitized_links.append(link)
            public_record["links"] = sanitized_links
        chosen_records.append(public_record)
        selected = []
        for event in histories[rid]:
            if event["id"] not in allowed_events:
                continue
            if _visibility(event["after"]) != "public":
                continue
            if event["before"] is not None and _visibility(event["before"]) != "public":
                continue
            redacted = dict(event)
            redacted["actor"] = {
                "id": "redacted", "kind": event["actor"]["kind"],
                "label": event["actor"]["label"] if event["actor"]["label"] in allowed_labels else "Contributor",
            }
            # Internal provenance identifiers are never public metadata.
            redacted["provenance"] = {"kind": event["provenance"]["kind"],
                                      "source_ref": None, "original_time": None}
            # Internal command identifiers are not part of public provenance.
            redacted["idempotency_key"] = "redacted"
            redacted["request_sha256"] = "redacted"
            redacted["operation_id"] = "redacted"
            selected.append(redacted)
            summary = dict(summaries[event["id"]])
            summary["actor_label"] = redacted["actor"]["label"]
            summary["operation_id"] = "redacted"
            chosen_summaries[event["id"]] = summary
        chosen_histories[rid] = selected
    return chosen_records, chosen_histories, chosen_summaries


def _rewrite_ineligible_record_refs(text: str, hidden_ids: set[str]) -> str:
    if not hidden_ids:
        return text
    hidden = set(hidden_ids)
    text = MARKDOWN_RECORD_LINK.sub(
        lambda match: "Unavailable in this view" if match.group(1) in hidden else match.group(0),
        text)
    return RECORD_REF.sub(lambda match: "Unavailable in this view"
                          if match.group(1) in hidden else match.group(0), text)


def _rewrite_snapshot_markdown_links(snapshot: str, links: list[dict], eligible_ids: set[str],
                                     source_path: str, hidden_paths: set[str]) -> str:
    marker = "\n---\n"
    if not snapshot.startswith("---\n") or marker not in snapshot[4:]:
        return _rewrite_markdown_links(snapshot, links, eligible_ids, source_path, hidden_paths)
    end = snapshot.index(marker, 4) + len(marker)
    return (snapshot[:end] + _rewrite_markdown_links(
        snapshot[end:], links, eligible_ids, source_path, hidden_paths))


def _rewrite_markdown_links(body: str, links: list[dict], eligible_ids: set[str],
                            source_path: str, hidden_paths: set[str]) -> str:
    """Replace current Markdown links that resolve to ineligible records.

    Link metadata gives the resolved record ID for ordinary links. Path
    matching also covers image links, which are intentionally omitted from
    navigable link metadata but must not expose a hidden record filename.
    """
    replacements = []
    link_index = 0
    for line_offset, match in _markdown_link_matches(body):
        target = match.group("target")
        is_image = match.group("prefix").startswith("!")
        target_id = None
        is_internal = False
        hidden_path = False
        if target.startswith("record:"):
            is_internal = True
            target_id = target[7:].split("#", 1)[0].lower()
        elif not (target.startswith(("http://", "https://", "mailto:"))
                  or EXTERNAL_SCHEME.match(target)):
            target_path = target.split("#", 1)[0]
            if target.startswith("#"):
                target_path = source_path
            elif target_path:
                target_path = posixpath.normpath(posixpath.join(
                    posixpath.dirname(source_path), target_path))
            else:
                target_path = source_path
            hidden_path = target_path in hidden_paths or posixpath.basename(target_path) in hidden_paths
            # Match git_source._record_links: structural indexes are not
            # navigable record metadata and therefore do not consume an entry
            # in the ordered record-link list.
            structural_index = target_path == "openwiki/index.md" or target_path.endswith("/index.md")
            is_internal = (target_path.endswith(".md") or target.startswith("#")) and not structural_index
        if is_internal and not is_image:
            if link_index < len(links):
                target_id = links[link_index].get("target_id") or target_id
            link_index += 1
        hidden_target = hidden_path or (target_id is not None and target_id not in eligible_ids)
        if hidden_target:
            replacements.append((line_offset + match.start(), line_offset + match.end(),
                                 "Unavailable in this view"))
        elif (is_internal and not is_image and target_id in eligible_ids
              and not target.startswith("record:")):
            fragment = "#" + target.split("#", 1)[1] if "#" in target else ""
            replacements.append((line_offset + match.start("target"),
                                 line_offset + match.end("target"),
                                 f"record:{target_id}{fragment}"))
    for start, end, replacement in reversed(replacements):
        body = body[:start] + replacement + body[end:]
    return body


def _markdown_link_matches(body: str):
    """Yield link matches outside fences, mirroring the source link parser."""
    in_fence = False
    fence_char = None
    offset = 0
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[0]
            if not in_fence:
                in_fence, fence_char = True, marker
            elif marker == fence_char:
                in_fence, fence_char = False, None
            offset += len(line)
            continue
        if not in_fence:
            for match in MARKDOWN_LINK.finditer(line):
                yield offset, match
        offset += len(line)


def _snapshot_body(snapshot: str | None) -> str | None:
    """Return Markdown body text from a complete frontmatter snapshot."""
    if snapshot is None:
        return None
    marker = "\n---\n"
    if not snapshot.startswith("---\n") or marker not in snapshot[4:]:
        return snapshot
    _, body = snapshot[4:].split(marker, 1)
    return body.strip()


def _snapshot_metadata(snapshot: str | None) -> dict:
    if snapshot is None:
        return {}
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "records"))
    from validate_v1 import frontmatter
    try:
        metadata, _ = frontmatter(snapshot)
        return metadata
    except (ValueError, TypeError) as exc:
        raise ProjectionError("invalid publication audit snapshot") from exc


def _add_private_snapshot(forbidden: set[str], snapshot: str | None):
    """Add full bytes and user-facing private metadata from an excluded source."""
    if not snapshot:
        return
    forbidden.add(snapshot)
    metadata = _snapshot_metadata(snapshot)
    # Include user supplied metadata that can be projected into catalogs,
    # reminders, search, aliases, or source links. Ignore very short values:
    # common labels such as "note" or "draft" would make a useful audit
    # impossible without adding meaningful privacy coverage.
    def add_metadata(value):
        if isinstance(value, str) and len(value) >= 8:
            forbidden.add(value)
        elif isinstance(value, dict):
            for child in value.values():
                add_metadata(child)
        elif isinstance(value, list):
            for child in value:
                add_metadata(child)

    add_metadata(metadata)
    for reminder in metadata.get("reminders", []):
        if isinstance(reminder, list) and len(reminder) == 2:
            when, text = reminder
            if isinstance(text, str) and text:
                forbidden.add(text)
            if isinstance(when, str) and len(when) >= 8:
                forbidden.add(when)
            elif isinstance(when, list):
                forbidden.update(value for value in when if isinstance(value, str) and len(value) >= 8)
    for source in metadata.get("sources", []):
        if isinstance(source, dict):
            for key in ("resource", "title"):
                value = source.get(key)
                if isinstance(value, str) and value:
                    forbidden.add(value)
    body = _snapshot_body(snapshot)
    if body and len(body) >= 8:
        forbidden.add(body)


def forbidden_public_references(records: list[dict], histories: dict[str, list[dict]],
                                selected_records: list[dict],
                                selected_histories: dict[str, list[dict]], *,
                                source_aliases: dict | None = None,
                                selected_aliases: dict | None = None) -> set[str]:
    """Collect source identities, paths and private text omitted from a release.

    This is a regression guard for *known* fixture/source material. It is not a
    classifier: a public record still needs human review for embedded private
    prose, URLs, or facts.
    """
    selected_record_ids = {record["id"] for record in selected_records}
    selected_event_ids = {
        event["id"] for events in selected_histories.values() for event in events
    }
    forbidden: set[str] = set()

    def add(value):
        if isinstance(value, str) and value:
            forbidden.add(value)

    for record in records:
        rid = record["id"]
        events = histories.get(rid, [])
        # Actor IDs never belong in a public projection, even for approved
        # public history; provenance and command IDs are similarly redacted.
        for event in events:
            add(event.get("actor", {}).get("id"))
            add(event.get("operation_id"))
            add(event.get("idempotency_key"))
            add(event.get("request_sha256"))
            provenance = event.get("provenance", {})
            add(provenance.get("source_ref"))

        if rid not in selected_record_ids:
            add(rid)
            private_path = record.get("path")
            add(private_path)
            if private_path:
                add(posixpath.basename(private_path))
            for event in events:
                for event_path in (event.get("path_before"), event.get("path_after")):
                    add(event_path)
                    if event_path:
                        add(posixpath.basename(event_path))
            _add_private_snapshot(forbidden, record.get("content"))

        for event in events:
            if event["id"] not in selected_event_ids:
                add(event.get("id"))
                for snapshot in (event.get("before"), event.get("after")):
                    # An eligible public current record can legitimately have
                    # the same bytes as an earlier unallowlisted public event.
                    # Scan omitted snapshots for private material specifically;
                    # full current records and all private transitions are
                    # independently audited below.
                    if snapshot is not None and _visibility(snapshot) == "private":
                        _add_private_snapshot(forbidden, snapshot)
    if source_aliases is not None:
        selected_aliases = selected_aliases or {"paths": {}, "entries": {}}
        source_paths = source_aliases.get("paths", {})
        selected_paths = selected_aliases.get("paths", {})
        for old_path, record_ids in source_paths.items():
            if old_path not in selected_paths:
                add(old_path)
                add(posixpath.basename(old_path))
            for rid in record_ids:
                if rid not in selected_record_ids:
                    add(rid)
        source_entries = source_aliases.get("entries", {})
        selected_entries = selected_aliases.get("entries", {})
        for source_ref, event_id in source_entries.items():
            if source_ref not in selected_entries:
                add(source_ref)
            if event_id not in selected_event_ids:
                add(event_id)
    # A private historical snapshot can belong to a record that is public and
    # currently allowlisted. Its record ID is therefore part of the public
    # route/catalog even though the private revision itself stays hidden.
    forbidden.difference_update(selected_record_ids)
    # Dates, lifecycle labels and tags may be intentionally published by a
    # different approved record. They are not private references *when that
    # exact value is independently present in authorized public frontmatter*.
    # Never exempt record/event IDs, paths, titles, descriptions or bodies.
    approved_shared_metadata = set()
    for record in selected_records:
        public_meta = _snapshot_metadata(record.get("content"))
        for field in ("status", "occurred_on", "occurred_at"):
            value = public_meta.get(field)
            if isinstance(value, str):
                approved_shared_metadata.add(value)
        for value in public_meta.get("tags", []):
            if isinstance(value, str):
                approved_shared_metadata.add(value)
    forbidden.difference_update(approved_shared_metadata)
    return forbidden


def audit_public(files: dict[str, bytes], forbidden: set[str], *,
                 policy_digest: str | None = None):
    """Byte-level denylist audit; run against every generated artifact.

    A denylist cannot establish that approved prose is safe: human review is
    still mandatory. Reject both direct UTF-8 and JSON-escaped occurrences.
    """
    inventory = {}
    for path, data in sorted(files.items()):
        if (not isinstance(path, str) or not path.endswith(".json")
                or Path(path).is_absolute() or ".." in Path(path).parts
                or "\\" in path or "\x00" in path or Path(path).as_posix() != path
                or not isinstance(data, bytes)):
            raise ProjectionError("unexpected public artifact")
        for secret in forbidden:
            if not secret:
                continue
            variants = (secret.encode("utf-8"), json.dumps(secret, ensure_ascii=True)[1:-1].encode("utf-8"))
            if any(variant in path.encode("utf-8") for variant in variants):
                raise ProjectionError(f"private reference detected in public artifact path: {path}")
            if any(variant in data for variant in variants):
                raise ProjectionError(f"private reference detected in public artifact: {path}")
        inventory[path] = hashlib.sha256(data).hexdigest()
    return {"artifacts": inventory, "count": len(inventory),
            "policy_digest": policy_digest}
