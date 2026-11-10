#!/usr/bin/env python3
"""Fail CI if new private OKF notes are added to this PUBLIC Git repository.

This is a source-history guard, separate from --public-only Pages export.
It does not determine whether a record's *content* is genuinely safe to share.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
# Two already-public historical source files are incorrectly marked private.
# Explicit exemptions do not make them secret or safe to keep publishing.
LEGACY_EXPOSED = {
    "openwiki/projects/knowledge-hub.md",
    "openwiki/projects/ivanovo-models.md",
}


def violations(root: Path) -> list[str]:
    wiki = root / "openwiki"
    errors = []
    for path in sorted(wiki.rglob("*.md")):
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        if not source.startswith("---\n"):
            continue
        pieces = source.split("\n---", 1)
        if len(pieces) != 2:
            errors.append(f"{relative}: invalid frontmatter delimiter")
            continue
        metadata = yaml.safe_load(pieces[0][4:])
        if not isinstance(metadata, dict):
            errors.append(f"{relative}: invalid OKF frontmatter")
            continue
        visibility = metadata.get("visibility")
        if visibility == "private" and relative not in LEGACY_EXPOSED:
            errors.append(f"{relative}: private-marked source in PUBLIC Git history")
        if (metadata.get("type") == "diary-entry"
                and relative.startswith("openwiki/journal/")
                and visibility != "public"):
            errors.append(f"{relative}: public-repo diary entries must be explicitly public")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = violations(args.root.resolve())
    if errors:
        raise SystemExit("Public source privacy audit failed:\n" + "\n".join(errors))
    print("Public source audit passed. Existing historical exposure still requires review.")


if __name__ == "__main__":
    main()
