"""Portable immutable source bundles for no-Git projection builds (#31).

A bundle contains the complete recursive Git tree manifest and raw blob bytes.
Its detached receipt is meaningful only when its exact digest is supplied via
an out-of-band trust channel (CLI expected-receipt-sha256).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path

from deterministic import ProjectionError, json_bytes

HEX_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def _hash_name(oid: str) -> str:
    if not HEX_OID.fullmatch(oid):
        raise ProjectionError("invalid Git object ID")
    return "sha1" if len(oid) == 40 else "sha256"


def _object_oid(kind: str, body: bytes, algorithm: str) -> str:
    framed = kind.encode("ascii") + b" " + str(len(body)).encode("ascii") + b"\0" + body
    return hashlib.new(algorithm, framed).hexdigest()


def _run_git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if result.returncode:
        raise ProjectionError("Git source failure: " + result.stderr.decode("utf-8", "replace"))
    return result.stdout


def _manifest_from_git(root: Path, commit: str) -> tuple[list[dict], dict[str, bytes]]:
    raw = _run_git(root, "ls-tree", "-r", "-z", "--full-tree", commit)
    entries, blobs = [], {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, sep, path_bytes = item.partition(b"\t")
        if not sep:
            raise ProjectionError("malformed Git tree listing")
        fields = header.split(b" ")
        if len(fields) != 3:
            raise ProjectionError("malformed Git tree entry")
        mode, kind, oid_b = fields
        try:
            path = path_bytes.decode("utf-8", "strict")
            mode_s, kind_s, oid = mode.decode("ascii"), kind.decode("ascii"), oid_b.decode("ascii")
        except UnicodeError as exc:
            raise ProjectionError("unsupported non-UTF-8 Git path") from exc
        if not path or path.startswith("/") or "\\" in path or any(p in ("", ".", "..") for p in path.split("/")):
            raise ProjectionError("unsafe path in Git tree")
        algorithm = _hash_name(oid)
        if kind_s not in ("blob", "commit") or mode_s not in ("100644", "100755", "120000", "160000"):
            raise ProjectionError("unsupported Git tree entry")
        entry = {"path": path, "mode": mode_s, "type": kind_s, "oid": oid}
        if kind_s == "blob":
            content = _run_git(root, "cat-file", "blob", oid)
            if _object_oid("blob", content, algorithm) != oid:
                raise ProjectionError("Git returned blob with mismatched object ID")
            entry["size"] = len(content)
            blobs[oid] = content
        entries.append(entry)
    entries.sort(key=lambda e: e["path"].encode("utf-8"))
    return entries, blobs


def _tree_oid(manifest: list[dict]) -> str:
    """Recompute the root tree OID from a complete recursive ls-tree manifest."""
    if not isinstance(manifest, list) or not manifest or any(not isinstance(item, dict) for item in manifest):
        raise ProjectionError("invalid tree manifest")
    if "oid" not in manifest[0] or not isinstance(manifest[0]["oid"], str):
        raise ProjectionError("invalid tree manifest object ID")
    algorithm = _hash_name(manifest[0]["oid"])
    if any("oid" not in item or not isinstance(item["oid"], str) or
           _hash_name(item["oid"]) != algorithm for item in manifest):
        raise ProjectionError("mixed or invalid Git object formats")
    leaves = {}
    seen_paths = []
    for item in manifest:
        if set(item) not in ({"path", "mode", "type", "oid", "size"},
                             {"path", "mode", "type", "oid"}):
            raise ProjectionError("invalid tree manifest fields")
        path = item["path"]
        if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path or any(p in ("", ".", "..") for p in path.split("/")):
            raise ProjectionError("unsafe tree manifest path")
        if path in leaves:
            raise ProjectionError("duplicate tree manifest path")
        mode, kind, oid = item.get("mode"), item.get("type"), item.get("oid")
        if mode not in ("100644", "100755", "120000", "160000") or kind not in ("blob", "commit"):
            raise ProjectionError("invalid tree manifest entry")
        if (kind == "commit") != (mode == "160000"):
            raise ProjectionError("Git tree mode and object type disagree")
        if not isinstance(oid, str) or not HEX_OID.fullmatch(oid) or _hash_name(oid) != algorithm:
            raise ProjectionError("invalid tree manifest object ID")
        if kind == "blob":
            if set(item) != {"path", "mode", "type", "oid", "size"} or type(item["size"]) is not int or item["size"] < 0:
                raise ProjectionError("invalid blob size in tree manifest")
        elif set(item) != {"path", "mode", "type", "oid"}:
            raise ProjectionError("invalid gitlink in tree manifest")
        leaves[path] = (mode, kind, oid)
        seen_paths.append(path.encode("utf-8"))
    if seen_paths != sorted(seen_paths):
        raise ProjectionError("tree manifest is not in canonical path order")
    paths = list(leaves)
    directories = {"/".join(parts[:i]) for path in paths
                    for parts in [path.split("/")] for i in range(1, len(parts))}
    if set(paths) & directories:
        raise ProjectionError("file/directory collision in tree manifest")

    def build(directory: str) -> str:
        entries = []
        prefix = directory + "/" if directory else ""
        for path, (mode, kind, oid) in leaves.items():
            if not path.startswith(prefix):
                continue
            rest = path[len(prefix):]
            if "/" not in rest:
                entries.append((rest.encode("utf-8"), mode, kind, oid))
        for child in directories:
            if child.rpartition("/")[0] == directory:
                name = child.rpartition("/")[2]
                entries.append((name.encode("utf-8"), "40000", "tree", build(child)))
        entries.sort(key=lambda e: e[0] + (b"/" if e[2] == "tree" else b""))
        payload = b"".join(mode.encode("ascii") + b" " + name + b"\0" + bytes.fromhex(oid)
                            for name, mode, _kind, oid in entries)
        return _object_oid("tree", payload, algorithm)

    return build("")


def manifest_digest(manifest: list[dict]) -> str:
    return hashlib.sha256(json_bytes({"manifest": manifest})).hexdigest()


def policy_digest_from_blobs(blobs: dict[str, bytes], manifest: list[dict]) -> str:
    policy = next((e for e in manifest if e["path"] == "config/publication.json" and e["type"] == "blob"), None)
    if policy is None:
        return hashlib.sha256(b"private-v1").hexdigest()
    return hashlib.sha256(blobs[policy["oid"]]).hexdigest()


def create_bundle(root: Path, revision: str, output: Path, receipt_output: Path) -> dict:
    root = Path(root).resolve()
    commit = _run_git(root, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    tree_hash = _run_git(root, "rev-parse", commit + "^{tree}").decode().strip()
    manifest, blobs = _manifest_from_git(root, commit)
    recomputed = _tree_oid(manifest)
    if recomputed != tree_hash:
        raise ProjectionError("complete manifest does not reproduce source tree hash")
    bundle = {"schema_version": 1, "commit": commit, "tree_hash": tree_hash,
              "manifest": manifest,
              "blobs": {oid: base64.b64encode(data).decode("ascii") for oid, data in sorted(blobs.items())}}
    bundle_raw = json_bytes(bundle)
    output = Path(output)
    receipt_output = Path(receipt_output)
    if output.exists() or output.is_symlink() or receipt_output.exists() or receipt_output.is_symlink():
        raise ProjectionError("bundle or receipt output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(bundle_raw)
    receipt = {"schema_version": 1, "commit": commit, "tree_hash": tree_hash,
               "bundle_digest": hashlib.sha256(bundle_raw).hexdigest(),
               "manifest_digest": manifest_digest(manifest),
               "policy_digest": policy_digest_from_blobs(blobs, manifest)}
    receipt_raw = json_bytes(receipt)
    receipt_output.write_bytes(receipt_raw)
    return {**receipt, "receipt_digest": hashlib.sha256(receipt_raw).hexdigest()}


def load_bundle(bundle_path: Path, receipt_path: Path, expected_receipt_sha256: str):
    """Validate external receipt and return immutable (commit, tree, manifest, blobs)."""
    try:
        bundle_raw = Path(bundle_path).read_bytes()
        receipt_raw = Path(receipt_path).read_bytes()
        if not re.fullmatch(r"[0-9a-f]{64}", expected_receipt_sha256):
            raise ProjectionError("expected receipt digest must be a lowercase SHA-256")
        if hashlib.sha256(receipt_raw).hexdigest() != expected_receipt_sha256:
            raise ProjectionError("trusted receipt digest mismatch")
        bundle = json.loads(bundle_raw, object_pairs_hook=_unique_pairs)
        receipt = json.loads(receipt_raw, object_pairs_hook=_unique_pairs)
    except ProjectionError:
        raise
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        raise ProjectionError("invalid source bundle or trusted receipt") from exc
    if (not isinstance(bundle, dict) or
            set(bundle) != {"schema_version", "commit", "tree_hash", "manifest", "blobs"} or
            type(bundle["schema_version"]) is not int or bundle["schema_version"] != 1):
        raise ProjectionError("unknown or incomplete source bundle schema")
    if (not isinstance(receipt, dict) or
            set(receipt) != {"schema_version", "commit", "tree_hash", "bundle_digest", "manifest_digest", "policy_digest"} or
            type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1):
        raise ProjectionError("unknown or incomplete trusted receipt schema")
    if hashlib.sha256(bundle_raw).hexdigest() != receipt["bundle_digest"]:
        raise ProjectionError("source bundle digest mismatch")
    if (bundle["commit"] != receipt["commit"] or bundle["tree_hash"] != receipt["tree_hash"] or
            manifest_digest(bundle["manifest"]) != receipt["manifest_digest"]):
        raise ProjectionError("source bundle does not match trusted receipt")
    if not isinstance(bundle["commit"], str) or not HEX_OID.fullmatch(bundle["commit"]):
        raise ProjectionError("invalid source commit ID")
    if not isinstance(bundle["tree_hash"], str) or not HEX_OID.fullmatch(bundle["tree_hash"]):
        raise ProjectionError("invalid source tree ID")
    if len(bundle["commit"]) != len(bundle["tree_hash"]):
        raise ProjectionError("mixed commit and tree object formats")
    if _tree_oid(bundle["manifest"]) != bundle["tree_hash"]:
        raise ProjectionError("source tree hash mismatch")
    if not isinstance(bundle["blobs"], dict):
        raise ProjectionError("invalid source bundle blob table")
    blob_bytes = {}
    expected_oids = {item["oid"] for item in bundle["manifest"] if item["type"] == "blob"}
    if set(bundle["blobs"]) != expected_oids:
        raise ProjectionError("source bundle does not contain every manifest blob")
    for oid, encoded in bundle["blobs"].items():
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ProjectionError("invalid embedded blob encoding") from exc
        if len(content) != next(item["size"] for item in bundle["manifest"] if item["oid"] == oid):
            raise ProjectionError("embedded blob size mismatch")
        if _object_oid("blob", content, _hash_name(oid)) != oid:
            raise ProjectionError("embedded Git blob object ID mismatch")
        blob_bytes[oid] = content
    if policy_digest_from_blobs(blob_bytes, bundle["manifest"]) != receipt["policy_digest"]:
        raise ProjectionError("source policy digest mismatch")
    return bundle["commit"], bundle["tree_hash"], bundle["manifest"], blob_bytes, receipt


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(create_bundle(args.root, args.revision, args.output, args.receipt_output), indent=2))
    except (ProjectionError, OSError, ValueError) as exc:
        parser.exit(1, f"source bundle failed: {exc}\n")


if __name__ == "__main__":
    main()
