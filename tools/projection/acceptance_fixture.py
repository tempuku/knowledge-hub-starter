"""Disposable Git fixtures built through the real v1 source writer."""
from __future__ import annotations

import subprocess
from pathlib import Path

import sys
RECORD_TOOLS = Path(__file__).resolve().parents[1] / "records"
sys.path.insert(0, str(RECORD_TOOLS))
import writer_v1 as writer


def uid(number: int) -> str:
    """Stable UUIDv4-shaped fixture identifiers (never production identities)."""
    return f"00000000-0000-4000-8000-{number:012x}"


class GitFixture:
    """Build a real committed source tree with writer-generated records/logs."""

    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self._run("init", "-q")
        self._run("config", "user.name", "Acceptance Fixture")
        self._run("config", "user.email", "fixture@example.invalid")
        self.files: dict[str, str] = {
            "openwiki/index.md": '---\nokf_version: "0.2"\n---\n\n# Fixture\n',
        }
        self.events: dict[str, list[dict]] = {}
        self.records: dict[str, dict] = {}
        self.next_id = 1
        self.last_revision: str | None = None

    def _run(self, *args: str) -> bytes:
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              capture_output=True).stdout

    def _id(self) -> str:
        result = uid(self.next_id)
        self.next_id += 1
        return result

    def add_record(self, path: str, source: str, *, recorded_at: str,
                   edits: list[tuple[str, str]] | None = None,
                   action: str = "UPDATED") -> str:
        """Create and optionally update a record with real writer primitives.

        edits contains (new canonical content, recorded_at) pairs. The first
        source uses create_source; each later snapshot is linked by a generated
        writer event and persisted in its sibling log.
        """
        rid = self._id()
        current = writer.create_source(source, rid)
        req = writer.normalized_request({
            "command": "create", "idempotency_key": self._id(),
            "actor": {"id": "fixture-actor", "kind": "agent", "label": "Fixture"},
            "summary": "Create acceptance record", "expected_head": "a" * 40,
            "path": path, "content": source,
        })
        eid, opid = self._id(), self._id()
        event = writer.make_event(req, record_id=rid, event_id=eid,
            operation_id=opid, sequence=1, action="CREATED", path_before=None,
            path_after=path, before=None, after=current, previous_event_id=None,
            recorded_at=recorded_at)
        history = writer.append_log(None, event)
        self.events[rid] = [event]
        for next_source, at in edits or []:
            if 'id: "' + rid + '"' not in next_source:
                # Accept a readable source-shaped revision in tests and add
                # the immutable generated fields exactly as the writer does.
                _, separator, tail = next_source.partition("\n")
                if separator == "" or not next_source.startswith("---\n"):
                    raise ValueError("fixture update must have frontmatter")
                next_source = (f'---\nid: "{rid}"\nschema_version: 1\n'
                               'visibility: "private"\n' + tail)
            next_req = writer.normalized_request({
                "command": "update", "idempotency_key": self._id(),
                "actor": {"id": "fixture-actor", "kind": "agent", "label": "Fixture"},
                "summary": "Update acceptance record", "expected_head": "a" * 40,
                "record_id": rid, "expected_version": event["id"],
                "content": next_source,
            })
            next_event = writer.make_event(next_req, record_id=rid,
                event_id=self._id(), operation_id=self._id(),
                sequence=len(self.events[rid]) + 1, action=action,
                path_before=path, path_after=path, before=current,
                after=next_source, previous_event_id=event["id"], recorded_at=at)
            history = writer.append_log(history, next_event)
            self.events[rid].append(next_event)
            current, event = next_source, next_event
        self.files[path] = current
        self.files[path[:-3] + ".log.md"] = history
        self.records[rid] = {"id": rid, "path": path, "content": current}
        return rid

    def commit(self, message: str = "fixture") -> str:
        for path, content in self.files.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        self._run("add", "-A")
        self._run("commit", "-qm", message)
        self.last_revision = self._run("rev-parse", "HEAD").decode().strip()
        return self.last_revision

    def move_record(self, record_id: str, destination: str, *, recorded_at: str) -> None:
        record = self.records[record_id]
        old_path = record["path"]
        current = record["content"]
        prior = self.events[record_id][-1]
        request = writer.normalized_request({
            "command": "move", "idempotency_key": self._id(),
            "actor": {"id": "fixture-actor", "kind": "agent", "label": "Fixture"},
            "summary": "Move acceptance record", "expected_head": "a" * 40,
            "record_id": record_id, "expected_version": prior["id"],
            "destination": destination,
        })
        event = writer.make_event(request, record_id=record_id,
            event_id=self._id(), operation_id=self._id(),
            sequence=len(self.events[record_id]) + 1, action="MOVED",
            path_before=old_path, path_after=destination, before=current,
            after=current, previous_event_id=prior["id"], recorded_at=recorded_at)
        old_log = old_path[:-3] + ".log.md"
        history = writer.append_log(self.files.pop(old_log), event)
        self.files.pop(old_path)
        self.files[destination] = current
        self.files[destination[:-3] + ".log.md"] = history
        self.events[record_id].append(event)
        self.records[record_id] = {**record, "path": destination}

    def mark_imported(self, record_id: str, source_ref: str) -> None:
        """Represent a deterministic legacy mapping with real log serialization."""
        events = self.events[record_id]
        if len(events) != 1 or events[0]["action"] != "CREATED":
            raise ValueError("fixture import marker applies to a single initial event")
        event = dict(events[0])
        event["action"] = "IMPORTED"
        event["actor"] = {"id": "migration-tool", "kind": "migration", "label": "Migration"}
        event["provenance"] = {
            "kind": "legacy-journal", "source_ref": source_ref,
            "original_time": event["recorded_at"],
        }
        self.events[record_id] = [event]
        path = self.records[record_id]["path"]
        self.files[path[:-3] + ".log.md"] = writer.append_log(None, event)


def note(title: str, body: str = "Body\n", *, status: str | None = None,
         extra: str = "") -> str:
    fields = f'type: note\ntitle: "{title}"\n'
    if status is not None:
        fields += f"status: {status}\n"
    return f"---\n{fields}{extra}---\n\n{body}"

