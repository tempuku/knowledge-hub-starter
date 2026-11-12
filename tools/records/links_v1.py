"""Pure W-03 link planning, consumed by later atomic move transactions.

Historical event snapshots must remain byte-identical. This module never
mutates the Git branch; the shared writer must authorize, validate and commit
every affected record and its corresponding event in one transaction.
"""
from __future__ import annotations

import posixpath
import re
import unicodedata

from validate_v1 import IntegrityError, safe_path

LINK = re.compile(r"(?P<prefix>!?\[[^\]\n]*\]\()(?P<target>[^)\s]+)(?P<suffix>\))")
EXTERNAL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def heading_slug(title: str) -> str:
    """Normalize ATX-heading text to the W-03 Unicode slug."""
    letters = []
    for char in title.lower().strip():
        if char.isspace():
            letters.append("-")
        elif char == "-" or unicodedata.category(char)[:1] in {"L", "N"}:
            letters.append(char)
    return "".join(letters)


def heading_fragments(markdown: str) -> set[str]:
    """Enumerate headings, with duplicate slugs suffixed -2, -3, etc."""
    seen = {}
    fragments = set()
    in_fence = False
    fence = None
    for line in markdown.splitlines():
        stripped = line.lstrip()
        if stripped.startswith((chr(96) * 3, "~" * 3)):
            marker = stripped[0]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence, fence = False, None
            continue
        if in_fence:
            continue
        match = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        slug = heading_slug(match.group(1))
        if not slug:
            continue
        index = seen.get(slug, 0) + 1
        seen[slug] = index
        fragments.add(slug if index == 1 else f"{slug}-{index}")
    return fragments


def _resolve(source_path: str, target: str):
    """Resolve a relative Markdown link, rejecting knowledge-root escape."""
    if target.startswith("/") or "\\" in target or "%" in target or "?" in target:
        raise IntegrityError("Unsupported or unsafe current relative link")
    destination = posixpath.normpath(
        posixpath.join(posixpath.dirname(source_path), target))
    if not destination.startswith("openwiki/") or destination == "openwiki":
        raise IntegrityError("Relative link escapes canonical knowledge root")
    if not destination.endswith(".md"):
        raise IntegrityError("Relative record link must target a Markdown file")
    return destination


def repair_relative_links(
    source: str, *, before_path: str, after_path: str,
    moved_paths: dict[str, str], current_sources: dict[str, str],
    record_ids: dict[str, str] | None = None,
    structural_indexes: set[str] | None = None,
) -> tuple[str, set[str]]:
    """Rebase relative links through a proposed atomic move plan.

    current_sources maps proposed post-move canonical paths to their Markdown
    content. Every linked target and fragment must resolve before commit.
    Transaction authorization belongs to the shared writer, not this helper.
    """
    safe_path(before_path, "before_path")
    safe_path(after_path, "after_path")
    for old, new in moved_paths.items():
        safe_path(old, "moved old path")
        safe_path(new, "moved new path")
    if after_path not in current_sources:
        raise IntegrityError("Moved source is missing from proposed transaction")
    targets = set()

    def rewrite(match):
        label, target, closing = match.group("prefix", "target", "suffix")
        if target.startswith("//"):
            raise IntegrityError("Protocol-relative links are not permitted")
        if target.startswith("#"):
            if target[1:] not in heading_fragments(current_sources[after_path]):
                raise IntegrityError("Same-record heading fragment is absent")
            return match.group(0)
        if target.startswith("record:"):
            identifier, _, fragment = target[len("record:"):].partition("#")
            if record_ids is not None:
                from validate_v1 import uid
                uid(identifier, "record link")
                path = record_ids.get(identifier)
                if path not in current_sources:
                    raise IntegrityError("Unresolved canonical record-ID link")
                if fragment and fragment not in heading_fragments(current_sources[path]):
                    raise IntegrityError("Unresolved canonical record heading")
            return match.group(0)
        if EXTERNAL.match(target):
            # Never treat script/file/data schemes as safe external links.
            if not target.startswith(("http://", "https://", "mailto:")):
                raise IntegrityError("Unsupported external Markdown link scheme")
            return match.group(0)
        if "#" in target:
            path_part, fragment = target.split("#", 1)
            if not fragment:
                raise IntegrityError("Empty heading fragment")
        else:
            path_part, fragment = target, None
        previous = _resolve(before_path, path_part)
        destination = moved_paths.get(previous, previous)
        if destination not in current_sources:
            if destination not in (structural_indexes or set()) or fragment:
                raise IntegrityError("Broken current relative record link")
        elif fragment and fragment not in heading_fragments(current_sources[destination]):
            raise IntegrityError("Heading fragment is absent from current target")
        targets.add(destination)
        relative = posixpath.relpath(destination, posixpath.dirname(after_path))
        updated = relative + ("#" + fragment if fragment else "")
        return label + updated + closing

    # Markdown code fences are literal text, not links to rewrite.
    result = []
    in_fence = False
    marker = None
    for line in source.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith((chr(96) * 3, "~" * 3)):
            kind = stripped[0]
            if not in_fence:
                in_fence, marker = True, kind
            elif kind == marker:
                in_fence, marker = False, None
            result.append(line)
        else:
            result.append(line if in_fence else LINK.sub(rewrite, line))
    return "".join(result), targets


def resolve_historical_path(path, logs, current_records):
    """Return an ID-based old-path resolution, or explicit ambiguous choices.

    logs is a map of current sibling paths to bytes; current_records is a map
    of current canonical paths to (record_id, title). The caller decides how
    to display choice links. An old path reused by another record must *never*
    silently redirect to either candidate.
    """
    from validate_v1 import parse_log
    from pathlib import PurePosixPath

    if not isinstance(path, str) or not path.startswith("openwiki/") or not path.endswith(".md"):
        raise IntegrityError("Invalid historical record path")
    candidates = {}
    for log_path, raw in logs.items():
        events = parse_log(raw, log_path)
        identifier = events[-1]["record_id"]
        current_path = events[-1]["path_after"]
        # The ID/title comes from canonical current record, not a stale snapshot.
        if current_path not in current_records:
            raise IntegrityError("Historical alias has no current record")
        current_id, title = current_records[current_path]
        if current_id != identifier:
            raise IntegrityError("Historical alias ID mismatch")
        if any(e["path_before"] == path or e["path_after"] == path for e in events):
            candidates[identifier] = {"record_id": identifier,
                                      "path": current_path, "title": title}
    for current_path, (identifier, title) in current_records.items():
        if current_path == path:
            candidates[identifier] = {"record_id": identifier,
                                      "path": current_path, "title": title}
    values = sorted(candidates.values(), key=lambda v: (v["title"], v["record_id"]))
    if not values:
        return {"kind": "not_found", "choices": []}
    if len(values) > 1:
        return {"kind": "ambiguous", "choices": values}
    return {"kind": "record", "record_id": values[0]["record_id"],
            "path": values[0]["path"]}
