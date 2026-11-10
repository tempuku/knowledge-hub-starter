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
from datetime import date, timedelta
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
        latest = date.fromisoformat(cls.latest_day)
        monday = latest - timedelta(days=latest.weekday())
        sunday = monday + timedelta(days=6)
        cls.week = [day for day in calendar["days"]
                    if monday.isoformat() <= day["date"] <= sunday.isoformat()]
        handler = functools.partial(QuietStaticFiles, directory=str(DIST))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://localhost:{cls.server.server_port}/"
        cls.playwright = sync_playwright().start()
        engine = os.environ.get("DIARY_BROWSER", "chromium")
        cls.browser = getattr(cls.playwright, engine).launch(headless=True)

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
        count = sum(day["count"] for day in self.week)
        expect(page.locator("#total")).to_have_text(self.entry_count_label(count))
        self.assertFalse(errors, "JavaScript errors on load: " + str(errors))
        return page

    @staticmethod
    def entry_count_label(count: int) -> str:
        return f"{count} {'entry' if count == 1 else 'entries'}"

    def test_initial_week_displays_entries_from_every_day(self):
        page = self.open_page(390, 844)
        expect(page.get_by_role("button", name="Week", exact=True)).to_have_attribute("aria-pressed", "true")
        headers = page.locator(".day-header")
        expect(headers).to_have_count(len(self.week))
        for i, day in enumerate(self.week):
            expect(headers.nth(i)).to_have_attribute("aria-expanded", "true")
            first_page = DIST / "data" / "days" / day["date"] / "1.json"
            titles = json.loads(first_page.read_text(encoding="utf-8"))
            notes = page.locator(".day").nth(i).locator(".note")
            expect(notes).to_have_count(len(titles))
            expect(notes.first).to_be_visible()

    def test_installable_home_screen_app_assets(self):
        page = self.open_page(1024, 768)
        expect(page.locator('meta[name="apple-mobile-web-app-capable"]')).to_have_attribute("content", "yes")
        expect(page.locator('link[rel="apple-touch-icon"]')).to_have_attribute("href", "./apple-touch-icon.png")
        expect(page.locator('link[rel="manifest"]')).to_have_attribute("href", "./manifest.webmanifest")
        result = page.evaluate("""async () => {
          const manifest = await (await fetch('./manifest.webmanifest')).json();
          const icon = await fetch('./apple-touch-icon.png');
          return { name: manifest.short_name, display: manifest.display, icon: icon.ok };
        }""")
        self.assertEqual(result, {"name": "Knowledge Hub", "display": "standalone", "icon": True})
        page.wait_for_function("navigator.serviceWorker.controller !== null")
        self.assertTrue(page.evaluate("""async () => {
          const script = document.querySelector('script[src*="app.js"]');
          return new URL(script.src).searchParams.has('v') && !!(await caches.match(script.src));
        }"""))

    def test_iphone_has_one_column_and_working_diary(self):
        page = self.open_page(390, 844)
        expect(page.locator(".library-sidebar")).to_be_hidden()
        expect(page.locator(".diary-content")).to_be_visible()
        self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        expect(page.locator(".note").first).to_be_visible()
        page.get_by_role("button", name="Open entry").first.click()
        expect(page.locator(".body").first).to_be_visible()

    def test_ipad_portrait_uses_split_view(self):
        page = self.open_page(768, 1024)
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
        expect(page.locator(".sidebar-day.active")).to_have_count(0)

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
        expect(page.locator("#total")).to_have_text(self.entry_count_label(self.latest_count))
        expect(page.locator(".sidebar-day.active")).to_have_count(1)
        expect(page.locator(".sidebar-day.active")).to_have_attribute("aria-current", "date")

    def test_day_week_month_navigation_and_lazy_loaded_entry(self):
        page = self.open_page(1024, 768)
        for view in ("Week", "Month", "Day"):
            page.get_by_role("button", name=view, exact=True).click()
            expect(page.locator(f'button[data-mode="{view.lower()}"]')).to_have_attribute("aria-pressed", "true")
        page.get_by_role("button", name="Open entry").first.click()
        expect(page.locator(".body").first).to_be_visible()
        self.assertGreater(len(page.locator(".body").first.inner_text()), 10)

    def test_history_opens_with_changed_lines_and_optional_snapshot(self):
        page = self.open_page(390, 844)
        expect(page.locator('#timeline a[href*="github.com"]')).to_have_count(0)
        history = page.locator(".note").filter(has_text="#history").first
        history.get_by_role("button", name="Show changes").click()
        expect(history.get_by_text("Changes in this entry", exact=False)).to_be_visible()
        expect(history.locator(".diff-added").first).to_be_visible()
        toggle = history.locator("summary").get_by_text("Original record")
        snapshot = history.locator("details .body")
        expect(snapshot).to_be_hidden()
        toggle.click()
        expect(snapshot).to_be_visible()
        toggle.click()
        expect(snapshot).to_be_hidden()
        expect(history.locator(".diff-added").first).to_be_visible()
        history.get_by_role("button", name="Hide changes").click()
        expect(history.locator(".diff-added").first).to_be_hidden()


if __name__ == "__main__":
    unittest.main()
