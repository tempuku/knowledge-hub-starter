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
    # The root must serve the actual v1 app, not only the legacy diary.
    if 'id="primary-nav"' not in html or 'href="#/records"' not in html:
        raise AssertionError("The live root is still the old Diary shell.")
    for asset in ("v1.js", "v1_data.js", "v1_diary.js", "v1_markdown.js", "v1.css",
                  "vendor/markdown-it-13.0.2.min.js"):
        if not get(asset):
            raise AssertionError("Missing v1 browser asset: " + asset)
    import re
    manifest = json.loads(get("data/manifest.json"))
    generation = manifest.get("generation", "")
    if (manifest.get("mode") != "public" or
            not re.fullmatch(r"[a-f0-9]{64}", generation) or
            manifest.get("root") != "g/" + generation + "/"):
        raise AssertionError("Invalid live public read-model generation")
    prefix = "data/g/" + generation + "/"
    catalog = json.loads(get(prefix + "catalog.json"))
    # Legacy entries are grouped into one record per canonical source path, so
    # the published event count, not the record count, must cover every
    # approved legacy diary entry. Demo records are checked by title below.
    if catalog.get("event_count", 0) < cal["total"]:
        raise AssertionError("Legacy diary entries missing in v1 event catalog")
    if catalog.get("record_count", 0) < 3:
        raise AssertionError("Public demo records missing in v1 catalog")
    pages = json.loads(get(prefix + "records/catalog/index.json"))
    items = []
    for page in pages["pages"]:
        items.extend(json.loads(get(prefix + page["url"]))["items"])
    titles = {item["title"] for item in items}
    required = {"Archon routing stack — public status",
                "Ivanovo Models — public project", "Personal Finance",
                "Идеи в одежде"}
    if not required.issubset(titles):
        raise AssertionError("Public Records/Projects UI is missing an in-progress record")
    demo = next(item for item in items if item["title"] ==
                "Recovery timeline (synthetic public demo)")
    if demo["status"] != "completed":
        raise AssertionError("Synthetic recovery is not completed")
    detail = json.loads(get(prefix + "records/" + demo["id"] + ".json"))
    if "October 27, 2026" not in detail.get("content", ""):
        raise AssertionError("Synthetic recovery record is not readable over HTTPS")
    if any(item["id"] == "5b82fc58-cccd-4997-ad93-b74b07ce3640"
           for item in items):
        raise AssertionError("Original private test record leaked publicly")
    print(f"Hosted v1 Records: {len(items)} entries, including public synthetic recovery")
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
