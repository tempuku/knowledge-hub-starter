#!/usr/bin/env python3
"""Fail when a change adds a public event that the allowlist does not approve (#126).

The publication allowlist is a reviewed repository change: a writer first
commits a public-marked record and its new event, then the trusted adapter adds
the matching record/event IDs to `config/publication.json` in a separate commit.
Until that second commit lands, the event must not be projected publicly. This
check therefore compares the changed v1 logs against the trusted base revision
and requires every *new* event of an already-allowlisted public record to be
allowlisted too. Historical events that were never allowlisted keep passing.

Use `--base <trusted-commit>` in CI. The check reads the allowlist and current
records from the working tree (CI checks out the pull-request commit) and reads
base history from Git. Legacy `# OKF Record Change Log` files, deleted records
and unparseable logs are skipped rather than guessed at; `validate_v1.py`
remains responsible for rejecting those on their own terms.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECTION = Path(__file__).resolve().parents[1] / "projection"
if str(PROJECTION) not in sys.path:
    sys.path.insert(0, str(PROJECTION))

from deterministic import ProjectionError
from publication import validate_policy
from validate_v1 import IntegrityError, parse_log, parse_record

LOG_HEADER = b"# Record history\n"
LOG_SUFFIX = ".log.md"
POLICY_PATH = "config/publication.json"


class CheckError(ValueError):
    """The check could not run; publication must fail closed."""


def git(root: Path, *args: str, missing_ok: bool = False) -> bytes | None:
    result = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode:
        if missing_ok:
            return None
        message = result.stderr.decode("utf-8", "replace").strip()
        raise CheckError(f"git {' '.join(args)}: {message}")
    return result.stdout


def warn(message: str) -> None:
    print(f"publication events: SKIP: {message}", file=sys.stderr)


def load_allowlist(root: Path) -> dict:
    """Validate the checked-out allowlist; a missing or malformed policy fails closed."""
    path = root / POLICY_PATH
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CheckError(f"{POLICY_PATH}: missing or unreadable publication allowlist") from exc
    try:
        policy, _ = validate_policy(raw)
    except ProjectionError as exc:
        raise CheckError(f"{POLICY_PATH}: invalid publication allowlist: {exc}") from exc
    return policy


def read_worktree(root: Path, path: str) -> bytes | None:
    """Read a current file without following symlinks; absent files mean deletion."""
    file = root / path
    try:
        if file.is_symlink() or not file.is_file():
            return None
        return file.read_bytes()
    except OSError:
        return None


def changed_logs(root: Path, base: str) -> list[str]:
    """Repository-relative logs changed by `base..HEAD`."""
    git(root, "rev-parse", "--verify", base + "^{commit}")
    raw = git(root, "diff", "--name-only", "--no-renames", f"{base}..HEAD", "--", "openwiki")
    return [line for line in raw.decode("utf-8", "strict").splitlines()
            if line.endswith(LOG_SUFFIX)]


def base_event_ids(root: Path, base: str, log_path: str) -> set[str] | None:
    """Event IDs already trusted at base, or None when no comparison is possible."""
    raw = git(root, "show", f"{base}:{log_path}", missing_ok=True)
    if raw is None:
        # The log is new, so every event in it is new by definition.
        return set()
    if not raw.startswith(LOG_HEADER):
        # A legacy base log has no v1 event IDs to compare against.
        return None
    try:
        return {event["id"] for event in parse_log(raw, log_path)}
    except (IntegrityError, ValueError) as exc:
        warn(f"{log_path}: cannot read base history ({exc})")
        return None


def unallowlisted_public_events(root: Path, base: str) -> tuple[list[str], int]:
    """Return readable failures and the number of new events that were checked."""
    policy = load_allowlist(root)
    allowed_records = set(policy["record_ids"])
    allowed_events = set(policy["event_ids"])
    failures: list[str] = []
    checked = 0
    for log_path in changed_logs(root, base):
        current = read_worktree(root, log_path)
        if current is None:
            continue  # A deleted log adds no event.
        if not current.startswith(LOG_HEADER):
            continue  # Legacy `# OKF Record Change Log` input is not the v1 store.
        try:
            events = parse_log(current, log_path)
        except (IntegrityError, ValueError) as exc:
            warn(f"{log_path}: cannot read current history ({exc})")
            continue
        known = base_event_ids(root, base, log_path)
        if known is None:
            continue
        new_events = [event for event in events if event.get("id") not in known]
        checked += len(new_events)
        if not new_events:
            continue
        record_path = log_path[:-len(LOG_SUFFIX)] + ".md"
        raw_record = read_worktree(root, record_path)
        if raw_record is None:
            continue  # A deleted record has no public projection.
        try:
            metadata, _ = parse_record(raw_record, record_path)
        except (IntegrityError, ValueError) as exc:
            warn(f"{record_path}: cannot read current record ({exc})")
            continue
        if metadata.get("visibility") != "public" or metadata["id"] not in allowed_records:
            continue
        for event in new_events:
            event_id = event.get("id")
            if not isinstance(event_id, str) or event_id in allowed_events:
                continue
            failures.append(
                f"{log_path}: sequence {event.get('sequence')} event {event_id} "
                f"belongs to allowlisted public record {metadata['id']} but is missing "
                f"from {POLICY_PATH} event_ids")
    return failures, checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."),
                        help="repository root (default: current directory)")
    parser.add_argument("--base", default="origin/main",
                        help="trusted Git base revision (default: origin/main)")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        failures, checked = unallowlisted_public_events(root, args.base)
    except (CheckError, OSError, ValueError) as exc:
        print(f"publication events: FAIL: {exc}", file=sys.stderr)
        return 1
    if failures:
        for failure in failures:
            print(f"publication events: FAIL: {failure}", file=sys.stderr)
        print(f"publication events: FAIL: {len(failures)} new public event(s) need a "
              f"reviewed {POLICY_PATH} entry", file=sys.stderr)
        return 1
    print(f"publication events: OK: {checked} new event(s) on changed v1 logs checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
