#!/usr/bin/env python3
"""Real-browser regression checks for the single responsive Knowledge Hub viewer.

Requires generated dist/ and Playwright Chromium. No external website is contacted:
a temporary local HTTP server serves the same static files as production.
"""
from __future__ import annotations

import functools
import json
import os
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DIST = (ROOT / os.environ.get("DIARY_DIST", "dist")).resolve()


class QuietStaticFiles(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class DiaryResponsiveBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (DIST / "index.html").is_file():
            raise RuntimeError("Build the static diary first: python tools/diary/build.py")
        calendar = json.loads((DIST / "data/calendar.json").read_text(encoding="utf-8"))
        if not calendar.get("days"):
            raise RuntimeError("Browser navigation tests need at least one fixture day")
        cls.latest_day = calendar["days"][0]["date"]
        cls.latest_count = calendar["days"][0]["count"]
        handler = functools.partial(QuietStaticFiles, directory=str(DIST))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def open_page(self, width: int, height: int):
        page = self.browser.new_page(viewport={"width": width, "height": height})
        self.addCleanup(page.close)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(self.url, wait_until="networkidle")
        expect(page.locator("#total")).to_have_text(f"{self.latest_count} records")
        self.assertFalse(errors, "JavaScript errors on load: " + str(errors))
        return page

    def test_iphone_has_one_column_and_working_diary(self):
        page = self.open_page(390, 844)
        expect(page.locator(".library-sidebar")).to_be_hidden()
        expect(page.locator(".diary-content")).to_be_visible()
        self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        expect(page.locator(".note").first).to_be_visible()
        page.get_by_role("button", name="Open entry").first.click()
        expect(page.locator(".body").first).to_be_visible()

    def test_ipad_portrait_uses_split_view(self):
        page = self.open_page(820, 1180)
        sidebar = page.locator(".library-sidebar")
        diary = page.locator(".diary-content")
        expect(sidebar).to_be_visible()
        expect(diary).to_be_visible()
        left = sidebar.bounding_box()
        right = diary.bounding_box()
        self.assertIsNotNone(left)
        self.assertIsNotNone(right)
        self.assertGreater(left["width"], 200)
        self.assertGreater(right["width"], 450)
        self.assertLessEqual(left["x"] + left["width"], right["x"] + 2)
        self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        expect(page.locator(".sidebar-day.active")).to_have_count(1)
        expect(page.locator(".sidebar-day.active")).to_have_attribute("aria-current", "date")

    def test_desktop_uses_full_width_ipad_layout_not_iphone_column(self):
        page = self.open_page(1440, 900)
        shell = page.locator(".app-shell").bounding_box()
        sidebar = page.locator(".library-sidebar").bounding_box()
        diary = page.locator(".diary-content").bounding_box()
        self.assertIsNotNone(shell)
        self.assertIsNotNone(sidebar)
        self.assertIsNotNone(diary)
        self.assertGreater(shell["width"], 1050, "Desktop must not keep the old 540px iPhone shell")
        self.assertGreaterEqual(sidebar["width"], 300)
        self.assertGreater(diary["width"], 700)
        self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))

    def test_sidebar_selection_restores_day_view(self):
        page = self.open_page(1024, 768)
        page.locator('#date').fill('1900-01-01')
        expect(page.locator(".empty")).to_be_visible()
        page.get_by_role("button", name="Week", exact=True).click()
        expect(page.locator('button[data-mode="week"]')).to_have_attribute("aria-pressed", "true")
        page.locator(".sidebar-day").first.click()
        expect(page.locator('button[data-mode="day"]')).to_have_attribute("aria-pressed", "true")
        self.assertEqual(page.locator("#date").input_value(), self.latest_day)
        expect(page.locator("#total")).to_have_text(f"{self.latest_count} records")
        expect(page.locator(".sidebar-day.active")).to_have_count(1)

    def test_day_week_month_navigation_and_lazy_loaded_entry(self):
        page = self.open_page(1024, 768)
        for view in ("Week", "Month", "Day"):
            page.get_by_role("button", name=view, exact=True).click()
            expect(page.locator(f'button[data-mode="{view.lower()}"]')).to_have_attribute("aria-pressed", "true")
        page.get_by_role("button", name="Open entry").first.click()
        expect(page.locator(".body").first).to_be_visible()
        self.assertGreater(len(page.locator(".body").first.inner_text()), 10)


if __name__ == "__main__":
    unittest.main()
