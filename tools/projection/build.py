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


def publish(root: Path | None, destination: Path, revision: str | None = None, *, mode: str = "private",
            bundle: Path | None = None, receipt: Path | None = None,
            receipt_sha256: str | None = None):
    if mode not in ("private", "public"):
        raise ProjectionError("unknown publication mode")
    if bundle is None:
        if root is None or not revision or receipt is not None or receipt_sha256 is not None:
            raise ProjectionError("Git builds require root and revision only")
        commit, tree, records, histories, summaries = load_revision(root, revision)
        bundle_policy = None
    else:
        if revision is not None or root is not None or receipt is None or receipt_sha256 is None:
            raise ProjectionError("no-Git builds require bundle, receipt and externally pinned receipt digest")
        commit, tree, records, histories, summaries, bundle_policy, _ = load_bundle(
            bundle, receipt, receipt_sha256)
    policy_digest = "private-v1"
    forbidden = set()
    source_aliases = derive_aliases(records, histories)
    aliases = source_aliases
    selected_aliases = source_aliases
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
        aliases = derive_aliases(records, histories)
        aliases["entries"] = {
            legacy_id: event_id for legacy_id, event_id in source_aliases["entries"].items()
            if event_id in selected_event_ids
        }
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
                        "published_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
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
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--receipt-sha256")
    args = parser.parse_args()
    try:
        root = None if args.bundle else args.root
        print(json.dumps(publish(root, args.destination, args.revision, mode=args.mode,
                                 bundle=args.bundle, receipt=args.receipt,
                                 receipt_sha256=args.receipt_sha256), indent=2))
    except (ProjectionError, OSError, ValueError) as exc:
        parser.exit(1, f"projection failed: {exc}\n")


if __name__ == "__main__":
    main()
