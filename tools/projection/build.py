"""Build and atomically publish immutable v1 read models.

This is opt-in and does not replace the legacy production diary builder.
Public mode uses the versioned allowlist and byte audit defined by #32.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from compose import build_projection
from deterministic import ProjectionError, generation_id, json_bytes, write_staging
from git_source import load_revision, load_bundle, derive_aliases, git
from publication import (load_policy, select_public, audit_public,
                         forbidden_public_references)

EXPORTER_VERSION = "v1-projection-0.3"


def _reviewed_aliases(raw: bytes | None, records, histories):
    """Validated optional aliases from the SAME immutable source generation."""
    import re
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ProjectionError("invalid immutable migration alias JSON") from exc
    if (type(data) is not dict or
            set(data) != {"schema_version", "source_revision", "paths", "entries", "current_entries"} or
            type(data["schema_version"]) is not int or data["schema_version"] != 1 or
            type(data["source_revision"]) is not str or
            not re.fullmatch("[0-9a-f]{40}", data["source_revision"])):
        raise ProjectionError("invalid reviewed migration alias schema")
    # Semantic validation of paths/IDs is performed by build_projection.
    if any(type(data[name]) is not dict for name in ("paths", "entries", "current_entries")):
        raise ProjectionError("invalid migration alias mappings")
    return data


def _read_aliases(root, commit, bundle, receipt, receipt_sha256):
    if bundle is None:
        try:
            return git(root, "show", f"{commit}:migration/aliases-v1.json")
        except ProjectionError:
            return None
    # Read the verified, externally pinned bundle, never local unpinned JSON.
    from sourcebundle import load_bundle as read_verified_bundle
    _, _, manifest, blobs, _ = read_verified_bundle(bundle, receipt, receipt_sha256)
    matches = [x for x in manifest if x["path"] == "migration/aliases-v1.json"]
    return blobs[matches[0]["oid"]] if matches else None


def _merge_aliases(derived, registry, record_ids, event_ids):
    result = {"paths": {k: list(v) for k, v in derived["paths"].items()},
              "entries": dict(derived["entries"])}
    if registry is None:
        return result
    result["current_entries"] = {}
    for old_path, ids in registry["paths"].items():
        eligible = sorted(set(ids) & record_ids)
        if eligible:
            current = result["paths"].get(old_path, [])
            result["paths"][old_path] = sorted(set(current) | set(eligible))
    for alias, eid in registry["entries"].items():
        if eid in event_ids:
            if alias in result["entries"] and result["entries"][alias] != eid:
                raise ProjectionError("contradictory reviewed migration entry alias")
            result["entries"][alias] = eid
    for alias, rid in registry["current_entries"].items():
        if rid in record_ids:
            result["current_entries"][alias] = rid
    return result


def publish(root: Path | None, destination: Path, revision: str | None = None, *, mode: str = "private",
            bundle: Path | None = None, receipt: Path | None = None,
            receipt_sha256: str | None = None,
            published_at: str | None = None,
            strict_native: bool = False):
    if mode not in ("private", "public"):
        raise ProjectionError("unknown publication mode")
    if bundle is None:
        if root is None or not revision or receipt is not None or receipt_sha256 is not None:
            raise ProjectionError("Git builds require root and revision only")
        commit, tree, records, histories, summaries = load_revision(
            root, revision, **({"strict_native": True} if strict_native else {}))
        bundle_policy = None
    else:
        if revision is not None or root is not None or receipt is None or receipt_sha256 is None:
            raise ProjectionError("no-Git builds require bundle, receipt and externally pinned receipt digest")
        commit, tree, records, histories, summaries, bundle_policy, _ = load_bundle(
            bundle, receipt, receipt_sha256,
            **({"strict_native": True} if strict_native else {}))
    policy_digest = "private-v1"
    forbidden = set()
    reviewed = _reviewed_aliases(
        _read_aliases(root, commit, bundle, receipt, receipt_sha256),
        records, histories)
    source_aliases = derive_aliases(records, histories)
    complete_ids = {r["id"] for r in records}
    complete_events = {e["id"] for chain in histories.values() for e in chain}
    aliases = _merge_aliases(source_aliases, reviewed, complete_ids, complete_events)
    selected_aliases = aliases
    if mode == "public":
        if bundle is None:
            policy_bytes = git(root, "show", f"{commit}:config/publication.json")
        else:
            policy_bytes = bundle_policy
        policy, policy_digest = load_policy(root, mode, revision_bytes=policy_bytes)
        original_records = records
        original_histories = histories
        records, histories, summaries = select_public(records, histories, summaries, policy)
        selected_event_ids = {event["id"] for events in histories.values() for event in events}
        # Path aliases come only from eligible events; record-level filtering
        # alone would retain an old private path on a currently public record.
        # Original provenance source_ref is internal evidence, even for an
        # allowlisted public event. Do NOT publish it as a route alias.
        # Only explicitly reviewed old UI IDs may be public event aliases.
        public_derived = derive_aliases(records, histories)
        public_derived["entries"] = {}
        aliases = _merge_aliases(
            public_derived, reviewed,
            {r["id"] for r in records}, selected_event_ids)
        selected_aliases = aliases
        forbidden.update(forbidden_public_references(
            original_records, original_histories, records, histories,
            source_aliases=source_aliases, selected_aliases=selected_aliases))
    generation = generation_id(tree, EXPORTER_VERSION, policy_digest)
    destination = destination.resolve()
    generation_dir = destination / "g" / generation
    manifest = destination / "manifest.json"
    if generation_dir.exists() or generation_dir.is_symlink():
        raise ProjectionError("immutable generation already exists; refusing overwrite")
    files = build_projection(records, histories, summaries, aliases=aliases)
    manifest_payload = {"schema_version": 1, "generation": generation,
                        "source_revision": commit, "exporter_version": EXPORTER_VERSION,
                        "policy_digest": policy_digest,
                        "published_at": (published_at if published_at is not None else
                                         dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")),
                        "mode": mode, "root": f"g/{generation}/"}
    if mode == "public":
        # Audit generated JSON and the exact root pointer bytes as one release
        # set before staging either artifact.
        audit_files = dict(files)
        audit_files["manifest.json"] = json_bytes(manifest_payload)
        audit_public(audit_files, forbidden, policy_digest=policy_digest)
    write_staging(generation_dir, files)
    # Publication point: manifest is the only mutable pointer. Write and fsync
    # its sibling temporary file before replacing it atomically.
    temp = manifest.with_name(".manifest.json.tmp")
    if temp.exists() or temp.is_symlink():
        raise ProjectionError("stale manifest staging path")
    try:
        with temp.open("xb") as handle:
            handle.write(json_bytes(manifest_payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, manifest)
    finally:
        temp.unlink(missing_ok=True)
    return manifest_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--revision")
    parser.add_argument("--mode", choices=("private", "public"), default="private")
    parser.add_argument("--native-only", action="store_true",
                        help="Fail closed on any unmigrated source or dated journal (M-04)")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--receipt-sha256")
    parser.add_argument("--published-at", help="fixed UTC timestamp for deterministic disposable rehearsal")
    args = parser.parse_args()
    try:
        root = None if args.bundle else args.root
        print(json.dumps(publish(root, args.destination, args.revision, mode=args.mode,
                                 bundle=args.bundle, receipt=args.receipt,
                                 receipt_sha256=args.receipt_sha256,
                                 published_at=args.published_at,
                                 strict_native=args.native_only), indent=2))
    except (ProjectionError, OSError, ValueError) as exc:
        parser.exit(1, f"projection failed: {exc}\n")


if __name__ == "__main__":
    main()
