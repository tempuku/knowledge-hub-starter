#!/usr/bin/env python3
"""End-to-end HTTP validation of the deployed, publicly readable diary.

Runs after GitHub Pages deployment (not against a local mock or test server).
Checks that actual hosted files and lazy diary JSON are reachable and consistent.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urljoin

parser = argparse.ArgumentParser()
parser.add_argument("url", help="Deployed HTTPS GitHub Pages root URL")
parser.add_argument("--min-records", type=int, default=1)
parser.add_argument("--attempts", type=int, default=15)
parser.add_argument("--retry-seconds", type=float, default=5.0)
args = parser.parse_args()

if not args.url.startswith("https://"):
    parser.error("Live validation must use an HTTPS URL.")
base = args.url.rstrip("/") + "/"


def get(path: str) -> bytes:
    url = urljoin(base, path)
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "KnowledgeHub-LiveSiteCheck/1.0", "Cache-Control": "no-cache"}),
        timeout=20,
    ) as response:
        if response.status != 200:
            raise AssertionError(f"Unexpected HTTP {response.status} for {url}")
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise AssertionError(f"Unexpectedly large file: {url}")
        return body


def check() -> int:
    html = get("index.html").decode("utf-8")
    script = get("app.js").decode("utf-8")
    style = get("style.css").decode("utf-8")
    if "Knowledge Hub" not in html or "calendar.json" not in script or ".library-sidebar" not in style:
        raise AssertionError("The hosted app shell does not match the expected real Knowledge Hub viewer.")

    cal = json.loads(get("data/calendar.json"))
    if cal.get("format") != "knowledge-hub-calendar-v1" or cal.get("total", 0) < args.min_records:
        raise AssertionError(f"The hosted diary has {cal.get('total')} records; expected at least {args.min_records}.")
    if not cal.get("days"):
        raise AssertionError("The hosted diary has no readable days.")
    first_day = cal["days"][0]["date"]
    day_meta = json.loads(get(f"data/days/{first_day}.json"))
    if day_meta.get("count", 0) <= 0:
        raise AssertionError("The first public date has no records.")
    notes = json.loads(get(f"data/days/{first_day}/1.json"))
    if not notes or not notes[0].get("title") or not notes[0].get("id"):
        raise AssertionError("The published day has no usable note summaries.")
    doc = json.loads(get("data/entries/" + quote(notes[0]["id"], safe="") + ".json"))
    if not doc.get("body") or doc.get("date") != first_day:
        raise AssertionError("A hosted entry cannot be opened by its ID.")
    print(f"Verified LIVE HTTPS Knowledge Hub: {base}")
    print(f"Hosted diary: {cal['total']} records; sample entry: {doc['title']}")
    return cal["total"]


for attempt in range(1, args.attempts + 1):
    try:
        check()
        break
    except (AssertionError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        if attempt == args.attempts:
            raise SystemExit(f"Live site validation failed after {attempt} attempts: {exc}")
        print(f"Live site not ready ({attempt}/{args.attempts}): {exc}", flush=True)
        time.sleep(args.retry_seconds)
