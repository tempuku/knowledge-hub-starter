"""Compare browser tokenization with the projection exporter's Python rules.

Run with the same Python minor version used by the projection build:
    python site/verify_v1_unicode.py

The deterministic vector places every Unicode code point between ASCII letters,
then checks NFC/lowercase, Unicode alphanumeric membership, underscore handling,
and the 2–64 code-point token limit. Output reports counts and a digest instead
of writing a large generated fixture into the repository.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def main() -> None:
    # A trailing space keeps each sampled code point in its own token context.
    text = "".join("a" + chr(codepoint) + "z " for codepoint in range(0x110000))
    normalized = __import__("unicodedata").normalize("NFC", text).lower()
    expected = list(dict.fromkeys(
        token for token in TOKEN_PATTERN.findall(normalized)
        if 2 <= len(token) <= 64
    ))
    canonical = json.dumps(expected, ensure_ascii=False, separators=(",", ":"))
    expected_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    js = r'''
const fs = require("fs");
const crypto = require("crypto");
const api = require(process.argv[1]);
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const result = api.tokens(input);
const digest = crypto.createHash("sha256").update(JSON.stringify(result), "utf8").digest("hex");
process.stdout.write(JSON.stringify({count: result.length, sha256: digest}));
'''
    completed = subprocess.run(
        ["node", "-e", js, str(ROOT / "v1_data.js")],
        input=json.dumps(text, ensure_ascii=True), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        raise SystemExit(completed.stderr or "Node parity runner failed")
    actual = json.loads(completed.stdout)
    expected_result = {"count": len(expected), "sha256": expected_digest}
    report = {
        "python_unicode_version": __import__("unicodedata").unidata_version,
        "sampled_codepoints": 0x110000,
        "python": expected_result,
        "javascript": actual,
        "match": actual == expected_result,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if actual != expected_result:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
