"""Regression tests for native-log event pages and deterministic UTC grouping."""
import json
import unittest

from deterministic import ProjectionError
from event_pages import build_event_pages, utc_day


class EventPageTests(unittest.TestCase):
    def event(self, eid, rid, seq, stamp, before, after):
        return {"id": eid, "record_id": rid, "sequence": seq, "recorded_at": stamp,
                "before": before, "after": after, "path_before": None,
                "path_after": "openwiki/notes/a.md"}

    def test_utc_rollover_and_exact_diff(self):
        self.assertEqual(utc_day("2026-11-13T00:30:00+03:00"), "2026-11-12")
        e = self.event("e1", "r1", 1, "2026-11-13T00:30:00+03:00", None, "hello\n")
        files = build_event_pages({"r1": [e]}, {"e1": {"id": "e1", "record_id": "r1",
            "sequence": 1, "recorded_at": e["recorded_at"]}})
        self.assertIn("days/2026-11-12/index.json", files)
        self.assertEqual(json.loads(files["calendar/2026.json"])["days"][0]["change_count"], 1)
        detail = json.loads(files["events/e1.json"])
        self.assertIn("+hello", detail["diff"]["text"])
        self.assertEqual(json.loads(files["history/r1/index.json"])["event_count"], 1)

    def test_day_pagination_and_distinct_records(self):
        events = [self.event(f"e{i}", "r1", i, "2026-11-12T12:00:00Z", None, "x\n")
                  for i in range(1, 52)]
        summaries = {e["id"]: {"id": e["id"], "record_id": "r1",
                    "sequence": e["sequence"], "recorded_at": e["recorded_at"]}
                     for e in events}
        files = build_event_pages({"r1": events}, summaries)
        day = json.loads(files["days/2026-11-12/index.json"])
        self.assertEqual((day["change_count"], day["record_count"]), (51, 1))
        self.assertEqual([p["count"] for p in day["pages"]], [50, 1])

    def test_duplicate_event_rejected(self):
        e = self.event("e1", "r1", 1, "2026-11-12T12:00:00Z", None, "x\n")
        with self.assertRaises(ProjectionError):
            build_event_pages({"r1": [e, e]}, {"e1": {"id": "e1", "record_id": "r1",
                "sequence": 1, "recorded_at": e["recorded_at"]}})

    def test_missing_timezone_rejected(self):
        with self.assertRaises(ProjectionError):
            utc_day("2026-11-12T12:00:00")


if __name__ == "__main__":
    unittest.main()
