#!/usr/bin/env python3
"""Trusted local Knowledge Hub v1 CLI; returns one JSON result on stdout."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from knowledge_service import (MAX_REQUEST_BYTES, WriterError,
                               decode_json, execute, new_writer)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path,
                        help="Trusted Git checkout root")
    parser.add_argument("--capability-file", required=True, type=Path,
                        help="Trusted JSON launch profile OUTSIDE the Git checkout")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--remote", default=None)
    parser.add_argument("--request", default="-",
                        help="JSON command file path, or '-' for stdin")
    return parser.parse_args()


def process(args):
    raw = (sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
           if args.request == "-" else
           Path(args.request).read_bytes())
    request = decode_json(raw, maximum=MAX_REQUEST_BYTES)
    writer = new_writer(root=args.root, capability_file=args.capability_file,
                        branch=args.branch, remote=args.remote)
    return execute(writer, request)


def main():
    try:
        result = process(arguments())
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except WriterError as exc:
        print(json.dumps(exc.response(), ensure_ascii=False, separators=(",", ":")))
        return 2
    except (ValueError, OSError, TypeError) as exc:
        safe = WriterError("WRITE_FAILED", "Trusted local CLI input unavailable",
                           retryable=True)
        print(json.dumps(safe.response(), ensure_ascii=False, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
