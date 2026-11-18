#!/usr/bin/env python3
"""Generate a synthetic v1 browser fixture through the transactional Git writer.

The fixture is deliberately disposable and contains no workspace records. Each
record change is made by GitRecordWriter, producing a real Git commit and
append-only event log before the projection builder is invoked.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "records"))
sys.path.insert(0, str(ROOT / "tools" / "projection"))
from service_v1 import GitRecordWriter


FIXTURE_ACTOR = {"id": "ui-acceptance-fixture", "kind": "agent", "label": "Fixture"}
SUMMARY = "Synthetic browser acceptance fixture"


def run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


class FixtureWriter:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        run(["git", "init", "-q", "-b", "main"], root)
        run(["git", "config", "user.name", "UI Acceptance Fixture"], root)
        run(["git", "config", "user.email", "fixture@example.invalid"], root)
        (root / ".githooks").mkdir()
        shutil.copy2(ROOT / ".githooks" / "pre-commit", root / ".githooks" / "pre-commit")
        (root / "tools" / "okf").parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT / "tools" / "okf", root / "tools" / "okf")
        wiki = root / "openwiki"
        wiki.mkdir()
        (wiki / "index.md").write_text('---\nokf_version: "0.2"\n---\n\n# Knowledge Hub\n', encoding="utf-8")
        run(["git", "add", "-A"], root)
        run(["git", "commit", "-qm", "fixture base"], root)
        self.seconds = 0
        self.clock_day = 8
        self.key_counter = 1
        self.writer = GitRecordWriter(
            root,
            {"repository_mode": "private", "operations": ["read", "create", "update", "move", "archive", "reopen"], "publisher_scope": False},
            staged_checker=self._validate_staged,
            clock=self._clock,
        )
        self.ids: dict[str, str] = {}
        self.versions: dict[str, str] = {}
        self.source_paths: dict[str, str] = {}
        self.event_ids: dict[str, list[str]] = {}

    def _clock(self):
        moment = datetime(2026, 11, self.clock_day, tzinfo=timezone.utc) + timedelta(seconds=self.seconds)
        self.seconds += 1
        return moment

    def set_day(self, day: int):
        self.clock_day = day
        self.seconds = 0

    def _validate_staged(self, workspace: Path):
        result = subprocess.run(["sh", str(workspace / ".githooks" / "pre-commit")], cwd=workspace,
                                capture_output=True)
        if result.returncode:
            raise RuntimeError("fixture staged validation failed: " + result.stderr.decode("utf-8", "replace"))

    def create(self, key: str, path: str, source: str):
        result = self.writer.write({
            "command": "create", "idempotency_key": self._key(), "actor": FIXTURE_ACTOR,
            "summary": SUMMARY, "expected_head": self._head(), "path": path, "content": source,
        })
        self.ids[key] = result["record_id"]
        self.versions[key] = result["version"]
        self.source_paths[key] = path
        self.event_ids[key] = [result["event_id"]]
        return result

    def update(self, key: str, source: str):
        rid = self.ids[key]
        source = source.replace("---\n", f'---\nid: "{rid}"\nschema_version: 1\n', 1)
        result = self.writer.write({
            "command": "update", "idempotency_key": self._key(), "actor": FIXTURE_ACTOR,
            "summary": SUMMARY, "expected_head": self._head(), "record_id": rid,
            "expected_version": self.versions[key], "content": source,
        })
        self.versions[key] = result["version"]
        self.event_ids[key].append(result["event_id"])
        return result

    def move(self, key: str, destination: str):
        result = self.writer.write({
            "command": "move", "idempotency_key": self._key(), "actor": FIXTURE_ACTOR,
            "summary": SUMMARY, "expected_head": self._head(), "record_id": self.ids[key],
            "expected_version": self.versions[key], "destination": destination,
        })
        self.versions[key] = result["version"]
        self.event_ids[key].append(result["event_id"])
        self.source_paths[key] = destination
        return result

    def archive(self, key: str):
        result = self.writer.write({
            "command": "archive", "idempotency_key": self._key(), "actor": FIXTURE_ACTOR,
            "summary": SUMMARY, "expected_head": self._head(), "record_id": self.ids[key],
            "expected_version": self.versions[key],
        })
        self.versions[key] = result["version"]
        self.event_ids[key].append(result["event_id"])
        return result

    def reopen(self, key: str):
        result = self.writer.write({
            "command": "reopen", "idempotency_key": self._key(), "actor": FIXTURE_ACTOR,
            "summary": SUMMARY, "expected_head": self._head(), "record_id": self.ids[key],
            "expected_version": self.versions[key], "status": "stable",
        })
        self.versions[key] = result["version"]
        self.event_ids[key].append(result["event_id"])
        return result

    def _key(self):
        value = f"00000000-0000-4000-8000-{self.key_counter:012x}"
        self.key_counter += 1
        return value

    def _head(self):
        return run(["git", "rev-parse", "HEAD"], self.root)


def source(title: str, body: str, *, kind: str = "note", status: str = "stable", tags: list[str] | None = None,
           reminders: list | None = None, project_id: str | None = None, extra: str = "") -> str:
    fields = [f"type: {kind}", f'title: "{title}"', f"status: {status}", 'visibility: "public"']
    if project_id:
        fields.append(f'project_id: "{project_id}"')
    if tags:
        fields.append("tags: [" + ", ".join(json.dumps(x, ensure_ascii=False) for x in tags) + "]")
    if reminders is not None:
        fields.append("reminders: " + json.dumps(reminders, ensure_ascii=False))
    fields.extend(extra.strip().splitlines())
    return "---\n" + "\n".join(fields) + "\n---\n\n" + body


def generate(source_dir: Path, dist_dir: Path, *, source_base: str = "source/") -> dict:
    if source_dir.exists():
        shutil.rmtree(source_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    fixture = FixtureWriter(source_dir)

    project = fixture.create("project", "openwiki/projects/field-notes/project.md", source(
        "Field Notes", "Project for synthetic navigation and related-record counts.\n", kind="project"))
    project_id = project["record_id"]
    fixture.set_day(9)

    # 54 events on one UTC day force a real generated 50-row page boundary.
    # Additional records below cover every date in the selected UTC week.
    main = fixture.create("main", "openwiki/projects/field-notes/records/cafe.md", source(
        "Café Δ field note", """A Unicode fixture for exact **AND** search, calendar and history.

<script>window.__fixtureScriptRan = true</script>
<img src="https://external.invalid/pixel.png" onerror="window.__fixtureImageRan=true">
[javascript](javascript:alert(1)) [data](data:text/html,unsafe) [file](file:///etc/passwd)

![tracking image](https://external.invalid/private-pixel.png)
""",
        tags=["resume", "field-note"], project_id=project_id,
        reminders=[[["2026-12-30", "2027-01-02"], "Cross month window"],
                   ["2026-11-15T09:00:00-05:00", "Offset timestamp"]],
    ))
    for index in range(1, 53):
        body = f"Update marker token-{index:02d}; shared exact-token.\n"
        if index == 10:
            body += "A creation-linked section.\n"
        latest_source = source("Café Δ field note", body, status=("completed" if index >= 20 else "stable"),
                               tags=["resume", "field-note"], project_id=project_id, reminders=[
                                   [["2026-12-30", "2027-01-02"], "Cross month window"],
                                   ["2026-11-15T09:00:00-05:00", "Offset timestamp"],
                               ])
        fixture.update("main", latest_source)

    # Move creates a current-vs-historical source path assertion; a second
    # record then reuses the old path, yielding a genuinely ambiguous alias.
    fixture.move("main", "openwiki/projects/field-notes/records/moved-cafe.md")
    fixture.set_day(11)
    fixture.create("day11", "openwiki/notes/daily/day-11.md", source(
        "Wednesday marker", "The selected UTC week has a Wednesday event.\n", tags=["day-marker"]))
    fixture.set_day(12)
    fixture.create("archived", "openwiki/notes/archive/retired.md", source(
        "Archived compass", "Archived content should be omitted from Today by default.\n", tags=["archive"]))
    fixture.archive("archived")

    fixture.set_day(13)
    fixture.create("large", "openwiki/notes/performance/large.md", source(
        "Large revision", "LARGE-START\n" + ("large detail fixture line. " * 12000) + "\nLARGE-END\n", tags=["large"]))

    fixture.set_day(14)
    fixture.create("body_hit", "openwiki/notes/search/body-hit.md", source(
        "Search body sample", "Café appears only in this body field.\n", tags=["search-sample"]))

    fixture.set_day(15)
    fixture.create("day15", "openwiki/notes/daily/day-15.md", source(
        "Sunday marker", "The selected UTC week has a Sunday event.\n", tags=["day-marker"]))

    fixture.create("no_history", "openwiki/notes/history/unpublished-events.md", source(
        "Public record without published history",
        "The current public record is visible, but its events are not allowlisted.\n",
        tags=["no-published-history"]))

    fixture.create("private", "openwiki/notes/private/never-export.md", source(
        "PRIVATE SENTINEL must never appear", "PRIVATE BODY SENTINEL browser guard.\n", tags=["private"]).replace('visibility: "public"', 'visibility: "private"'))

    # This is deliberately the final writer operation: the real writer must
    # validate the moved record against its trusted base before a newer record
    # occupies the old path, and the resulting alias is then unambiguous only
    # by explicit title choice. Policy is committed below without another write.
    fixture.set_day(10)
    fixture.create("reuse", "openwiki/projects/field-notes/records/cafe.md", source(
        "Reused legacy path", "A second eligible record now occupies the old path.\n", tags=["reuse"], project_id=project_id))

    # A real committed publication policy explicitly allows current public
    # records, their approved histories, and one source-file record.
    public_keys = ["project", "main", "reuse", "day11", "archived", "large", "body_hit", "day15", "no_history"]
    policy = {
        "schema_version": 1,
        "record_ids": sorted(fixture.ids[k] for k in public_keys),
        "event_ids": sorted(event_id for k in public_keys if k != "no_history" for event_id in fixture.event_ids[k]),
        "actor_labels": ["Fixture"],
    }
    # GitRecordWriter publishes commits by updating the shared branch ref while
    # leaving its disposable fixture worktree untouched. Resync this synthetic
    # checkout before the separate policy commit so stale index state cannot
    # accidentally delete writer-generated records.
    run(["git", "reset", "--hard", "HEAD"], source_dir)
    config = source_dir / "config"
    config.mkdir()
    (config / "publication.json").write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run(["git", "add", "config/publication.json"], source_dir)
    run(["git", "commit", "-qm", "fixture publication policy"], source_dir)
    revision = run(["git", "rev-parse", "HEAD"], source_dir)

    # Build a public projection. The approved source endpoint is copied only
    # for `main`, whose exact current ID is recorded in the app configuration.
    from build import publish
    manifest = publish(source_dir, dist_dir / "data", revision=revision, mode="public")
    current = subprocess.run(["git", "show", f"{revision}:{fixture.source_paths['main']}"],
                             cwd=source_dir, check=True, capture_output=True).stdout
    safe_dir = dist_dir / "source"
    safe_dir.mkdir(parents=True, exist_ok=True)
    (safe_dir / Path(fixture.source_paths["main"]).name).write_bytes(current)
    (dist_dir / "v1-config.js").write_text(
        "window.KnowledgeHubConfig = " + json.dumps({
            "publicSourceRecordIds": [fixture.ids["main"]],
            "publicSourcePaths": {fixture.ids["main"]: Path(fixture.source_paths["main"]).name},
            "sourceURLBase": source_base,
        }) + ";\n", encoding="utf-8")
    site = ROOT / "site"
    for filename in ("v1.html", "v1.js", "v1.css", "v1_data.js", "v1_markdown.js", "style.css",
                     "index.html", "app.js", "sw.js", "manifest.webmanifest"):
        candidate = site / filename
        if not candidate.is_file():
            raise RuntimeError(f"generated-v1 static asset is missing: {candidate}")
        shutil.copy2(candidate, dist_dir / filename)
    vendor = site / "vendor"
    if not vendor.is_dir():
        raise RuntimeError("generated-v1 Markdown vendor directory is missing")
    shutil.copytree(vendor, dist_dir / "vendor")
    app_html = dist_dir / "v1.html"
    app_text = app_html.read_text(encoding="utf-8")
    if "v1-config.js" not in app_text:
        app_text = app_text.replace('<script src="./v1_data.js"',
                                    '<script src="./v1-config.js" defer></script>\n  <script src="./v1_data.js"', 1)
    app_html.write_text(app_text, encoding="utf-8")
    summary = {
        "kind": "synthetic-v1-browser-acceptance",
        "source_revision": revision,
        "generation": manifest["generation"],
        "mode": manifest["mode"],
        "record_count": len(policy["record_ids"]),
        "event_count": len(policy["event_ids"]),
        "public_source_record_id": fixture.ids["main"],
        "current_source_path": fixture.source_paths["main"],
        "historical_source_path": "openwiki/projects/field-notes/records/cafe.md",
        "archived_record_id": fixture.ids["archived"],
        "large_record_id": fixture.ids["large"],
        "body_hit_record_id": fixture.ids["body_hit"],
        "no_history_record_id": fixture.ids["no_history"],
        "project_id": fixture.ids["project"],
        "main_event_ids": fixture.event_ids["main"],
        "reminder_record_id": fixture.ids["main"],
    }
    (dist_dir / "fixture-report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (source_dir / "fixture-private-test-only.json").write_text(
        json.dumps({"private_record_id": fixture.ids["private"]}) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--source-base", default="source/")
    args = parser.parse_args()
    print(json.dumps(generate(args.source_dir.resolve(), args.dist_dir.resolve(), source_base=args.source_base), indent=2))


if __name__ == "__main__":
    main()
