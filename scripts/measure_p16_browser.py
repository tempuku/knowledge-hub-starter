#!/usr/bin/env python3
"""Local-only real-browser P16 timing on a generated synthetic *private* v1 tree.

No user data. Operates on the full deterministic 10k/100k private projection,
served only from 127.0.0.1. Chromium 4x CPU and 10 Mbit/s/100 ms RTT emulation
are applied through CDP; WebKit acceptance remains a separate local suite.
Browser timings measured here must not be passed off as physical iPad results.
"""
from __future__ import annotations

import argparse
import functools
import json
import shutil
import sys
import tempfile
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
NETWORK_BYTES_PER_SECOND = 10_000_000 // 8
LATENCY_MS = 100
CPU_SLOWDOWN = 4
REQUIRED_ASSETS = ("v1.html", "v1.js", "v1.css", "v1_data.js",
                   "v1_markdown.js", "style.css", "index.html", "sw.js")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def prepare_site(destination: Path) -> None:
    site = ROOT / "site"
    for name in REQUIRED_ASSETS:
        shutil.copy2(site / name, destination / name)
    shutil.copytree(site / "vendor", destination / "vendor")
    html = destination / "v1.html"
    content = html.read_text(encoding="utf-8")
    # An explicit source configuration is harmless in a local private build.
    (destination / "v1-config.js").write_text(
        'window.KnowledgeHubConfig = {"publicSourceRecordIds":[],"publicSourcePaths":{}};\n',
        encoding="utf-8",
    )
    if "v1-config.js" not in content:
        content = content.replace('<script src="./v1_data.js"',
                                  '<script src="./v1-config.js" defer></script>\n  <script src="./v1_data.js"', 1)
    html.write_text(content, encoding="utf-8")


def set_throttling(context, page) -> None:
    session = context.new_cdp_session(page)
    session.send("Emulation.setCPUThrottlingRate", {"rate": CPU_SLOWDOWN})
    session.send("Network.emulateNetworkConditions", {
        "offline": False, "latency": LATENCY_MS,
        "downloadThroughput": NETWORK_BYTES_PER_SECOND,
        "uploadThroughput": NETWORK_BYTES_PER_SECOND,
    })


def sample(browser, url: str, *, route: str, expected_heading: str | None) -> tuple[float, int]:
    from playwright.sync_api import expect
    context = browser.new_context(viewport={"width": 1440, "height": 900},
                                  service_workers="block")
    page = context.new_page()
    set_throttling(context, page)
    deadline = {"at": None}
    bytes_total = 0

    def on_response(response):
        nonlocal bytes_total
        try:
            bytes_total += max(0, int(response.headers.get("content-length", "0")))
        except ValueError:
            pass
        if expected_heading is None and response.url.endswith("/data/manifest.json"):
            deadline["at"] = time.monotonic()
        elif expected_heading is not None and "/records/00000000-0000-4000-8000-000000000001.json" in response.url:
            deadline["at"] = time.monotonic()

    page.on("response", on_response)
    try:
        page.goto(url + route, wait_until="domcontentloaded", timeout=60000)
        if expected_heading is None:
            expect(page.locator(".event-row").first).to_be_visible(timeout=60000)
        else:
            expect(page.get_by_role("heading", name=expected_heading, exact=True)).to_be_visible(timeout=60000)
        finish = time.monotonic()
        if deadline["at"] is None:
            raise RuntimeError("Required manifest/detail response was not observed; do not claim a timing pass")
        return round((finish - deadline["at"]) * 1000, 1), bytes_total
    finally:
        context.close()


def run(dist: Path, build_report: dict) -> dict:
    from playwright.sync_api import sync_playwright
    manifest = json.loads((dist / "data/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("mode") != "private":
        raise ValueError("Must measure isolated synthetic private fixture, never a public deployment")
    if manifest.get("source_revision") != build_report.get("fixture_source_revision"):
        raise ValueError("Browser and build measurement source revisions differ")
    prepare_site(dist)
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(dist)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/v1.html"
    diary_times, record_times, diary_bytes, record_bytes = [], [], [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                browser_version = browser.version
                for _ in range(3):
                    time_ms, transferred = sample(browser, url, route="", expected_heading=None)
                    diary_times.append(time_ms)
                    diary_bytes.append(transferred)
                    time_ms, transferred = sample(
                        browser, url, route="#/records/00000000-0000-4000-8000-000000000001",
                        expected_heading="t000000δ",
                    )
                    record_times.append(time_ms)
                    record_bytes.append(transferred)
            finally:
                browser.close()
            # Report the version without counting desktop WebKit as a P16
            # throttled measurement or as actual iPad acceptance.
            webkit = playwright.webkit.launch(headless=True)
            try:
                webkit_version = webkit.version
            finally:
                webkit.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    report = json.loads(json.dumps(build_report))
    report["diary_after_manifest_ms"] = diary_times
    report["record_after_response_ms"] = record_times
    report["transfer_bytes"] = {
        "diary_samples": diary_bytes, "record_samples": record_bytes,
    }
    report["environment"].update({
        "browser_chromium": browser_version,
        "browser_webkit": webkit_version,
        "network_mbit": 10, "rtt_ms": LATENCY_MS, "cpu_slowdown": CPU_SLOWDOWN,
    })
    report["browser_status"] = "measured-throttled-chromium-only"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.dist.resolve(), json.loads(args.build_report.read_text(encoding="utf-8")))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"P16 browser evidence failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
