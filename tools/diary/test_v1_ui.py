#!/usr/bin/env python3
"""Generated-v1 end-to-end browser acceptance for Chromium and WebKit.

Run the real-Git fixture generator first, then set V1_DIST. The test serves the
generated projection and the same static v1 app assets locally; no live site or
user data is involved. Missing fixture capabilities are hard failures.
"""
from __future__ import annotations

import functools
import json
import os
import re
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urljoin

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DIST = Path(os.environ.get("V1_DIST", ROOT / "dist-v1-ui-fixture")).resolve()
SOURCE_DIR = Path(os.environ.get("V1_SOURCE_DIR", DIST.parent / "v1-ui-source")).resolve()
ARTIFACTS = Path(os.environ.get("V1_UI_ARTIFACTS", DIST / "browser-artifacts")).resolve()
ENGINE = os.environ.get("V1_BROWSER", "chromium")
REQUIRED_BROWSERS = {"chromium", "webkit"}


class QuietStaticFiles(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


class GeneratedV1BrowserAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if ENGINE not in REQUIRED_BROWSERS:
            raise RuntimeError("V1_BROWSER must be chromium or webkit")
        for name in ("v1.html", "v1.js", "v1_data.js", "v1_markdown.js", "v1.css", "fixture-report.json"):
            if not (DIST / name).is_file():
                raise RuntimeError(f"generated v1 fixture is incomplete: missing {name}")
        if not (DIST / "data" / "manifest.json").is_file():
            raise RuntimeError("generated v1 fixture is incomplete: missing data/manifest.json")
        cls.fixture = json.loads((DIST / "fixture-report.json").read_text(encoding="utf-8"))
        private_test = SOURCE_DIR / "fixture-private-test-only.json"
        if not private_test.is_file():
            raise RuntimeError("synthetic private-route guard fixture is missing")
        cls.private_record_id = json.loads(private_test.read_text(encoding="utf-8"))["private_record_id"]
        cls.manifest = json.loads((DIST / "data" / "manifest.json").read_text(encoding="utf-8"))
        if cls.fixture.get("kind") != "synthetic-v1-browser-acceptance":
            raise RuntimeError("not the generated synthetic v1 browser fixture")
        if cls.manifest.get("mode") != "public" or cls.manifest.get("generation") != cls.fixture.get("generation"):
            raise RuntimeError("fixture manifest/policy does not match the generated public fixture")
        if cls.fixture.get("record_count", 0) < 4 or cls.fixture.get("event_count", 0) < 51:
            raise RuntimeError("fixture is missing the multi-record or >50 event scenario")
        if not cls.fixture.get("public_source_record_id") or len(cls.fixture.get("main_event_ids", [])) < 50:
            raise RuntimeError("fixture lacks source-link or historical event coverage")

        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietStaticFiles, directory=str(DIST)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/v1.html"
        cls.playwright = sync_playwright().start()
        executable = os.environ.get("V1_BROWSER_EXECUTABLE")
        cls.browser = getattr(cls.playwright, ENGINE).launch(headless=True, executable_path=executable or None)
        cls.browser_version = cls.browser.version
        cls.case_reports = []
        cls.screenshots = []
        cls.test_to_acceptance = {
            "test_default_diary_week_route_range_and_exact_counts": ["U1", "U7", "U8", "U24"],
            "test_routes_back_forward_filters_focus_and_refresh": ["U2", "U3", "U17"],
            "test_diary_day_navigation_pagination_and_filtered_totals": ["U2", "U3", "U7", "U8", "U14"],
            "test_current_record_markdown_sanitization_source_and_historical_heading": ["U4", "U21", "U23"],
            "test_revision_creation_move_and_current_status_are_distinct": ["U5", "U6"],
            "test_search_unicode_and_filter_intersection_no_fuzzy_invention": ["U9", "U10"],
            "test_calendar_reminder_cross_month_and_separate_diary_empty_day": ["U11", "U12"],
            "test_today_sections_and_archived_exclusion": ["U13"],
            "test_project_overview_counts_current_non_archived_records": ["U7"],
            "test_detail_gates_full_payload_until_explicit_action": ["U22"],
            "test_public_payload_privacy_guard_and_scoped_request_surface": ["U15", "U16"],
            "test_accessibility_landmarks_keyboard_and_focus": ["U19"],
            "test_responsive_widths_targets_and_200_percent_zoom": ["U20"],
            "test_missing_and_ambiguous_routes_are_generic_and_safe": ["U18"],
            "test_offline_public_shell_is_explicitly_labelled": ["U15"],
            "test_retry_is_scoped_to_one_diary_day": ["U14"],
            "test_generation_refresh_preserves_route_and_switches_manifest": ["U17"],
            "test_rapid_search_response_order_keeps_latest_query": ["U10"],
            "test_no_store_native_request_is_not_cached_or_fallen_back": ["U15", "U16"],
        }

    @classmethod
    def tearDownClass(cls):
        report = {
            "kind": "synthetic-v1-browser-acceptance",
            "engine": ENGINE,
            "browser_version": cls.browser_version,
            "playwright_version": "1.56.0",
            "fixture_source_revision": cls.fixture["source_revision"],
            "generation": cls.fixture["generation"],
            "fixture_counts": {"records": cls.fixture["record_count"], "events": cls.fixture["event_count"]},
            "tests": cls.case_reports,
            "screenshots": cls.screenshots,
        }
        (ARTIFACTS / f"{ENGINE}-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1440, "height": 1000})
        self.requests = []
        self.inflight = set()
        self.max_concurrent = 0
        def requested(request):
            self.requests.append({
                "path": request.url.split(self.url.rsplit("/", 1)[0], 1)[-1].split("?", 1)[0],
                "resource_type": request.resource_type,
            })
            self.inflight.add(id(request))
            self.max_concurrent = max(self.max_concurrent, len(self.inflight))
        self.page.on("request", requested)
        self.page.on("requestfinished", lambda request: self.inflight.discard(id(request)))
        self.page.on("requestfailed", lambda request: self.inflight.discard(id(request)))
        self.page_errors = []
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        self.page.goto(self.url, wait_until="networkidle")
        expect(self.page.locator("#route-content")).not_to_have_attribute("aria-busy", "true", timeout=15000)
        self.assertEqual(self.page_errors, [], "JavaScript exception on launch: " + repr(self.page_errors))

    def tearDown(self):
        name = self.id().rsplit(".", 1)[-1]
        paths = sorted({r["path"].replace(self.private_record_id, "<synthetic-private-id>") for r in self.requests})
        self.case_reports.append({"name": name, "acceptance_ids": self.test_to_acceptance.get(name, []),
                                  "max_concurrent_requests": self.max_concurrent,
                                  "network_request_count": len(self.requests),
                                  "requested_paths": paths})
        self.page.close()

    def screenshot(self, name: str):
        path = ARTIFACTS / f"{ENGINE}-{name}.png"
        self.page.screenshot(path=str(path), full_page=True)
        self.screenshots.append(path.name)

    def navigate(self, hash_route: str):
        self.page.evaluate("route => { location.hash = route; }", hash_route)

    def test_default_diary_week_route_range_and_exact_counts(self):
        self.assertRegex(self.page.evaluate("location.hash"), r"^#/diary(?:\?|$)")
        # Hashless first launch resolves to the latest event's full UTC week.
        expect(self.page.get_by_role("button", name="Week", exact=True)).to_have_attribute("aria-pressed", "true")
        expect(self.page.get_by_text(re.compile(r"UTC"))).to_be_visible()
        expect(self.page.get_by_role("heading", level=1)).to_be_visible()
        expect(self.page.get_by_text(re.compile(r"\b61 changes\b.*\b7 records\b"))).to_be_visible()
        day_headers = self.page.locator(".diary-day > button")
        expect(day_headers).to_have_count(7)
        for header in day_headers.all():
            expect(header).to_have_attribute("aria-expanded", "true")
        self.assertLessEqual(self.max_concurrent, 4, "initial Diary exceeded the four-request concurrency budget")
        requested = [item["path"] for item in self.requests]
        self.assertFalse(any(re.search(r"/(?:records|events)/[^/]+\.json$", path) for path in requested),
                         "initial Diary fetched a body or event detail before selection")
        self.assertFalse(any("search/" in path for path in requested), "initial Diary fetched search shards")
        self.assertFalse(any(self.private_record_id in path for path in requested),
                         "initial Diary requested the synthetic private record ID")
        self.screenshot("default-week")

    def test_routes_back_forward_filters_focus_and_refresh(self):
        self.navigate("#/records?q=caf%C3%A9&tag=resume")
        expect(self.page.get_by_role("heading", name="Records", exact=True)).to_be_visible()
        expect(self.page.get_by_text("Café Δ field note", exact=True)).to_be_visible()
        self.page.go_back()
        expect(self.page.get_by_role("button", name="Week", exact=True)).to_have_attribute("aria-pressed", "true")
        self.page.go_forward()
        expect(self.page.get_by_text("Café Δ field note", exact=True)).to_be_visible()
        self.page.reload(wait_until="networkidle")
        expect(self.page.get_by_text("Café Δ field note", exact=True)).to_be_visible()

    def test_diary_day_navigation_pagination_and_filtered_totals(self):
        # The latest week has 61 events over seven records. Load more is explicit
        # and does not mutate the exact range total.
        label = self.page.get_by_text(re.compile(r"\b61 changes\b.*\b7 records\b"))
        expect(label).to_be_visible()
        initial = self.page.locator(".event-row").count()
        self.assertGreaterEqual(initial, 1)
        load_more = self.page.get_by_role("button", name=re.compile(r"Load more", re.I))
        if initial < 61:
            expect(load_more).to_be_visible()
            load_more.first.click()
            expect(self.page.get_by_text(re.compile(r"\b61 changes\b.*\b7 records\b"))).to_be_visible()
        date_input = self.page.locator('input[type="date"]')
        self.assertEqual(date_input.count(), 1, "Diary must expose a labelled date control")
        date_input.fill("2026-11-09")
        self.page.get_by_role("button", name="Day", exact=True).click()
        expect(self.page.get_by_role("button", name="Day", exact=True)).to_have_attribute("aria-pressed", "true")
        self.assertIn("date=2026-11-09", self.page.evaluate("location.hash"))
        expect(self.page.get_by_text(re.compile(r"\b54 changes\b.*\b1 record\b"))).to_be_visible()
        self.page.get_by_role("button", name=re.compile(r"Load more", re.I)).click()
        expect(self.page.locator(".event-row")).to_have_count(54)

    def test_current_record_markdown_sanitization_source_and_historical_heading(self):
        rid = self.fixture["public_source_record_id"]
        self.navigate(f"#/records/{rid}?tab=content")
        expect(self.page.get_by_role("heading", name="Café Δ field note", exact=True)).to_be_visible()
        self.assertFalse(self.page.evaluate("window.__fixtureScriptRan === true"))
        self.assertEqual(self.page.locator("img[src^='https://external.invalid']").count(), 0)
        self.assertEqual(self.page.locator("script:not([src])").count(), 0)
        for unsafe in ("javascript:", "data:text/html", "file:///etc/passwd"):
            self.assertEqual(self.page.locator(f'a[href^="{unsafe}"]').count(), 0)
        expect(self.page.get_by_role("link", name="Source", exact=True)).to_be_visible()
        self.page.get_by_role("link", name="Source", exact=True).click()
        source_file = DIST / "source" / "moved-cafe.md"
        expect(self.page.locator(".source-text")).to_be_visible()
        self.assertEqual(self.page.locator(".source-text").evaluate("el => el.textContent"),
                         source_file.read_text(encoding="utf-8"),
                         "Source tab must preserve the exact current source bytes")
        self.navigate("#/diary?date=2026-11-09&mode=day")
        file_link = self.page.get_by_role("link", name=re.compile(r"File:.*moved-cafe\.md", re.I)).first
        expect(file_link).to_be_visible()
        self.assertIn("moved-cafe.md", file_link.get_attribute("href") or "")
        self.assertEqual(file_link.get_attribute("target"), "_blank")
        event_title = self.page.get_by_role("heading", name="Café Δ field note", exact=True).first
        expect(event_title).to_be_visible()
        self.assertFalse(event_title.locator("a").count(), "historical title must remain plain text")
        source_link_url = file_link.get_attribute("href")
        self.assertTrue(source_link_url)
        self.page.goto(urljoin(self.url, source_link_url), wait_until="domcontentloaded")
        expect(self.page.locator("body")).to_contain_text('id: "' + rid + '"')
        self.assertFalse((DIST / "source" / "cafe.md").exists(),
                         "historical path must not be the source-link target")

    def test_revision_creation_move_and_current_status_are_distinct(self):
        event_ids = self.fixture["main_event_ids"]
        self.navigate(f"#/events/{event_ids[0]}?view=before")
        expect(self.page.get_by_text("This record did not exist before this change.", exact=True)).to_be_visible()
        self.navigate(f"#/events/{event_ids[-2]}?view=revision")
        expect(self.page.get_by_text("You are viewing a past revision", exact=True)).to_be_visible()
        self.navigate(f"#/events/{event_ids[-1]}?view=diff")
        expect(self.page.get_by_text(re.compile(r"Content unchanged; moved from"))).to_be_visible()
        expect(self.page.get_by_text(re.compile(r"Revision\s+\d+"))).to_be_visible()
        expect(self.page.get_by_role("link", name="Open current record")).to_be_visible()

    def test_search_unicode_and_filter_intersection_no_fuzzy_invention(self):
        self.navigate("#/records?q=caf%C3%A9")
        expect(self.page.get_by_text("Café Δ field note", exact=True)).to_be_visible()
        expect(self.page.get_by_text("Search body sample", exact=True)).to_be_visible()
        main_hit = self.page.get_by_text("Café Δ field note", exact=True).first.bounding_box()
        body_hit = self.page.get_by_text("Search body sample", exact=True).first.bounding_box()
        self.assertIsNotNone(main_hit)
        self.assertIsNotNone(body_hit)
        self.assertLess(main_hit["y"], body_hit["y"], "title hits must rank above body-only hits")
        self.navigate(f"#/records?project={self.fixture['project_id']}&type=note&status=completed&area=projects%2Ffield-notes&tag=resume")
        expect(self.page.get_by_text("Café Δ field note", exact=True)).to_be_visible()
        expect(self.page.get_by_text("Search body sample", exact=True)).to_have_count(0)
        self.navigate("#/records?status=deprecated")
        expect(self.page.get_by_text("Archived compass", exact=True)).to_be_visible()
        expect(self.page.get_by_text(re.compile(r"\b1\s+record\b"))).to_be_visible()
        self.navigate("#/records?q=caf%C3%A9%20nevermatch")
        expect(self.page.get_by_text("No matching records.", exact=True)).to_be_visible()
        expect(self.page.get_by_role("button", name=re.compile(r"Clear filters", re.I))).to_be_visible()

    def test_calendar_reminder_cross_month_and_separate_diary_empty_day(self):
        self.navigate("#/calendar?month=2026-11")
        expect(self.page.get_by_text("Offset timestamp", exact=True)).to_be_visible()
        expect(self.page.get_by_text(re.compile(r"2026-11-15.*-05:00"))).to_be_visible()
        self.navigate("#/calendar?month=2026-12")
        expect(self.page.get_by_text("Important dates are not notifications.", exact=True)).to_be_visible()
        expect(self.page.get_by_text("Cross month window", exact=True)).to_be_visible()
        expect(self.page.get_by_text(re.compile(r"2026-12-30.*2027-01-02"))).to_be_visible()
        self.navigate("#/diary?date=2026-12-30&mode=day")
        expect(self.page.get_by_text("No changes in this period.", exact=True)).to_be_visible()
        expect(self.page.get_by_role("link", name=re.compile(r"View calendar", re.I))).to_be_visible()

    def test_today_sections_and_archived_exclusion(self):
        self.navigate("#/today")
        expect(self.page.get_by_role("heading", name="Today", exact=True)).to_be_visible()
        expect(self.page.get_by_text("Archived compass", exact=True)).to_have_count(0)
        self.assertEqual(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), True)

    def test_project_overview_counts_current_non_archived_records(self):
        project_id = self.fixture["project_id"]
        self.navigate(f"#/projects/{project_id}")
        expect(self.page.get_by_role("heading", name="Field Notes", exact=True)).to_be_visible()
        self.page.get_by_role("link", name="Records", exact=True).click()
        expect(self.page.get_by_text("Café Δ field note", exact=True)).to_be_visible()
        expect(self.page.get_by_text("Reused legacy path", exact=True)).to_be_visible()
        expect(self.page.get_by_text(re.compile(r"\b2 records\b"))).to_be_visible()

    def test_detail_gates_full_payload_until_explicit_action(self):
        rid = self.fixture["large_record_id"]
        self.navigate(f"#/records/{rid}")
        expect(self.page.get_by_text(re.compile(r"Load full (content|record)", re.I))).to_be_visible()
        detail_request = f"records/{rid}.json"
        self.assertFalse(any(detail_request in item["path"] for item in self.requests),
                         "large detail bytes were requested before explicit consent")
        self.page.get_by_role("button", name=re.compile(r"Load full (content|record)", re.I)).click()
        expect(self.page.get_by_text("LARGE-END", exact=False)).to_be_visible(timeout=15000)
        self.assertTrue(any(detail_request in item["path"] for item in self.requests))

    def test_public_payload_privacy_guard_and_scoped_request_surface(self):
        public_bytes = b"".join(path.read_bytes() for path in DIST.rglob("*") if path.is_file() and "browser-artifacts" not in path.parts)
        self.assertNotIn(b"PRIVATE SENTINEL", public_bytes)
        self.assertNotIn(b"PRIVATE BODY SENTINEL", public_bytes)
        privateish = [path for path in self.requests if "private" in path["path"].lower()]
        self.assertEqual(privateish, [], "browser requested a private-named payload")
        self.assertTrue(all(request["path"].startswith(("/v1.html", "/v1.js", "/v1.css", "/style.css", "/v1_data.js", "/v1_markdown.js", "/v1-config.js", "/vendor/", "/data/manifest.json", "/data/g/", "/source/")) for request in self.requests),
                        "browser fetched a URL outside the generated app/projection/source fixture")

    def test_accessibility_landmarks_keyboard_and_focus(self):
        expect(self.page.get_by_role("banner")).to_be_visible()
        expect(self.page.get_by_role("navigation", name="Primary navigation")).to_be_visible()
        expect(self.page.get_by_role("main")).to_be_visible()
        expect(self.page.get_by_role("link", name="Skip to content")).to_be_visible()
        self.page.keyboard.press("/")
        expect(self.page.get_by_role("searchbox", name="Search records")).to_be_focused()
        self.page.keyboard.press("Escape")
        self.assertEqual(self.page_errors, [], "keyboard interaction raised JavaScript errors")

    def test_responsive_widths_targets_and_200_percent_zoom(self):
        for width in (320, 390, 768, 1024, 1440):
            self.page.set_viewport_size({"width": width, "height": 900})
            self.page.wait_for_timeout(50)
            overflow = self.page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
            self.assertFalse(overflow, f"horizontal page overflow at {width}px")
            if width in (320, 390, 768, 1024, 1440):
                self.screenshot(f"width-{width}")
        self.page.evaluate("document.documentElement.style.zoom = '200%'")
        self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"),
                         "horizontal page overflow at 200% zoom")
        controls = self.page.get_by_role("button").all()
        for button in controls:
            box = button.bounding_box()
            if box and button.is_visible():
                self.assertGreaterEqual(box["height"], 40, f"undersized touch target: {button.inner_text()!r}")

    def test_missing_and_ambiguous_routes_are_generic_and_safe(self):
        self.navigate("#/records/ffffffff-ffff-4fff-8fff-ffffffffffff")
        expect(self.page.get_by_text("Record unavailable in this view", exact=True)).to_be_visible()
        self.navigate(f"#/records/{self.private_record_id}")
        expect(self.page.get_by_text("Record unavailable in this view", exact=True)).to_be_visible()
        private_requests = [request["path"] for request in self.requests if self.private_record_id in request["path"]]
        self.assertTrue(all(path.endswith(f"records/{self.private_record_id}.meta.json") for path in private_requests),
                        "private direct route requested a private record body")
        self.navigate("#/not-a-route")
        expect(self.page.get_by_text("Page not found", exact=True)).to_be_visible()
        expect(self.page.get_by_role("link", name="Go to diary")).to_be_visible()
        old_path = self.fixture["historical_source_path"]
        self.navigate("#/records/" + quote(old_path, safe=""))
        expect(self.page.get_by_text("Choose a record", exact=True)).to_be_visible()
        expect(self.page.get_by_role("link", name="Café Δ field note", exact=True)).to_be_visible()
        expect(self.page.get_by_role("link", name="Reused legacy path", exact=True)).to_be_visible()

    def test_offline_public_shell_is_explicitly_labelled(self):
        self.page.context.set_offline(True)
        self.page.reload(wait_until="domcontentloaded")
        expect(self.page.get_by_text(re.compile(r"Offline|saved data", re.I))).to_be_visible(timeout=5000)
        self.page.context.set_offline(False)

    def test_retry_is_scoped_to_one_diary_day(self):
        failed = {"done": False}
        def abort_one(route):
            if not failed["done"] and re.search(r"/days/2026-11-09/1\.json$", route.request.url):
                failed["done"] = True
                route.abort()
            else:
                route.continue_()
        self.page.route("**/days/**/1.json", abort_one)
        self.page.reload(wait_until="domcontentloaded")
        if not failed["done"]:
            self.page.wait_for_timeout(1000)
        self.assertTrue(failed["done"], "fixture day page was not requested for the targeted retry test")
        expect(self.page.get_by_text("Could not load this resource", exact=True)).to_be_visible(timeout=10000)
        expect(self.page.get_by_role("button", name="Retry", exact=True)).to_be_visible()
        rows_before = self.page.locator(".event-row").count()
        self.page.get_by_role("button", name="Retry", exact=True).click()
        expect(self.page.get_by_text("Could not load this resource", exact=True)).to_have_count(0)
        self.assertGreaterEqual(self.page.locator(".event-row").count(), rows_before,
                                "retry removed previously loaded day rows")

    def test_generation_refresh_preserves_route_and_switches_manifest(self):
        old = json.loads((DIST / "data" / "manifest.json").read_text(encoding="utf-8"))
        changed = dict(old, generation="f" * 64, source_revision="e" * 40)
        fetches = {"count": 0}
        def manifest(route):
            fetches["count"] += 1
            if fetches["count"] == 1:
                route.continue_()
            else:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(changed))
        self.page.route("**/data/manifest.json", manifest)
        self.page.get_by_role("button", name="Refresh", exact=True).click()
        expect(self.page.get_by_text(re.compile(r"Update available\. Refresh to load the new published generation\."))).to_be_visible()
        self.page.get_by_role("button", name="Refresh", exact=True).click()
        expect(self.page.get_by_role("button", name="Week", exact=True)).to_have_attribute("aria-pressed", "true")
        self.assertRegex(self.page.evaluate("location.hash"), r"^#/diary")

    def test_rapid_search_response_order_keeps_latest_query(self):
        held = []
        first = {"value": True}
        def delay_first(route):
            if first["value"] and "search/" in route.request.url:
                first["value"] = False
                held.append(route)
            else:
                route.continue_()
        self.page.route("**/search/**", delay_first)
        search = self.page.get_by_role("searchbox", name="Search records")
        search.fill("cafe")
        search.press("Enter")
        self.page.wait_for_timeout(450)
        search.fill("definitelynomatch")
        search.press("Enter")
        expect(self.page.get_by_text("No matching records.", exact=True)).to_be_visible(timeout=10000)
        for route in held:
            route.continue_()
        self.page.wait_for_timeout(200)
        expect(self.page.get_by_text("No matching records.", exact=True)).to_be_visible()

    def test_no_store_native_request_is_not_cached_or_fallen_back(self):
        self.page.route("**/data/g/private-probe.json", lambda route: route.fulfill(
            status=200, content_type="application/json", headers={"cache-control": "no-store"},
            body='{"private_probe":"synthetic-only"}'))
        self.page.evaluate("""async () => {
          if (!navigator.serviceWorker) throw new Error('Service workers unavailable');
          await navigator.serviceWorker.register('./sw.js');
          await navigator.serviceWorker.ready;
        }""")
        self.page.reload(wait_until="domcontentloaded")
        self.page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=10000)
        result = self.page.evaluate("""async () => {
          const url = new URL('./data/g/private-probe.json', location.href).href;
          const response = await fetch(new Request(url, {cache:'no-store'}));
          const payload = await response.text();
          const cached = await caches.match(url);
          return {status:response.status, payload:payload, cached:!!cached};
        }""")
        self.assertEqual(result, {"status": 200, "payload": '{"private_probe":"synthetic-only"}', "cached": False})
        self.page.context.set_offline(True)
        offline = self.page.evaluate("""async () => {
          const url = new URL('./data/g/private-probe.json', location.href).href;
          try { await fetch(new Request(url, {cache:'no-store'})); return false; }
          catch (error) { return true; }
        }""")
        self.page.context.set_offline(False)
        self.assertTrue(offline, "an offline no-store request fell back to cached content")


if __name__ == "__main__":
    unittest.main(verbosity=2)
