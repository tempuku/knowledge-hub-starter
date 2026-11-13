"""Build and atomically publish immutable private v1 read models.

This is opt-in and does not replace the legacy production diary builder.
Public publishing is deliberately disabled until the #32 privacy gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from compose import build_projection
from deterministic import ProjectionError, generation_id, json_bytes, write_staging
from git_source import load_revision, git
from publication import load_policy, select_public, audit_public

EXPORTER_VERSION = "v1-projection-0.2"


def publish(root: Path, destination: Path, revision: str, *, mode: str = "private"):
    if mode not in ("private", "public"):
        raise ProjectionError("unknown publication mode")
    commit, tree, records, histories, summaries = load_revision(root, revision)
    policy_digest = "private-v1"
    forbidden = set()
    if mode == "public":
        policy_bytes = git(root, "show", f"{commit}:config/publication.json")
        policy, policy_digest = load_policy(root, mode, revision_bytes=policy_bytes)
        original_records = records
        original_histories = histories
        records, histories, summaries = select_public(records, histories, summaries, policy)
        selected_record_ids = {r["id"] for r in records}
        selected_event_ids = {event["id"] for events in histories.values() for event in events}
        # Audit every source identifier that policy/eligibility actually omitted.
        # Allowlisting a currently private record or private-before event must
        # never exempt its references from the public byte scan.
        for record in original_records:
            if record["id"] not in selected_record_ids:
                forbidden.add(record["id"])
                forbidden.add(record["path"])
                forbidden.update(event["id"] for event in original_histories[record["id"]])
            else:
                for event in original_histories[record["id"]]:
                    if event["id"] not in selected_event_ids:
                        forbidden.add(event["id"])
            # Actor IDs are always redacted from the public projection.
            forbidden.update(event["actor"]["id"] for event in original_histories[record["id"]])
    generation = generation_id(tree, EXPORTER_VERSION, policy_digest)
    destination = destination.resolve()
    generation_dir = destination / "g" / generation
    manifest = destination / "manifest.json"
    if generation_dir.exists() or generation_dir.is_symlink():
        raise ProjectionError("immutable generation already exists; refusing overwrite")
    files = build_projection(records, histories, summaries)
    if mode == "public":
        audit_public(files, forbidden)
    write_staging(generation_dir, files)
    # Publication point: manifest is the only mutable pointer. Write and fsync
    # its sibling temporary file before replacing it atomically.
    manifest_payload = {"schema_version": 1, "generation": generation,
                        "source_revision": commit, "exporter_version": EXPORTER_VERSION,
                        "policy_digest": policy_digest,
                        "published_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                        "mode": mode, "root": f"g/{generation}/"}
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
    parser.add_argument("--revision", required=True)
    parser.add_argument("--mode", choices=("private", "public"), default="private")
    args = parser.parse_args()
    try:
        print(json.dumps(publish(args.root, args.destination, args.revision, mode=args.mode), indent=2))
    except (ProjectionError, OSError, ValueError) as exc:
        parser.exit(1, f"projection failed: {exc}\n")


if __name__ == "__main__":
    main()
