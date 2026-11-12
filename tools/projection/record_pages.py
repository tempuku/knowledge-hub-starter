"""P-02 deterministic current-record catalog and detail read models.

Input records are validated, eligible canonical snapshots with current metadata.
This module never reads or changes the production builder.
"""
from __future__ import annotations

from deterministic import ProjectionError, json_bytes, paginate

SUMMARY_FIELDS = ("id", "title", "description", "type", "status",
                  "project_id", "tags", "area", "updated_at", "version",
                  "content_bytes")


def build_record_pages(records: list[dict]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    summaries = []
    seen = set()
    for record in records:
        if any(field not in record for field in SUMMARY_FIELDS) or "content" not in record or "path" not in record:
            raise ProjectionError("incomplete canonical record metadata")
        rid = record["id"]
        if not isinstance(rid, str) or not rid or "/" in rid or "\\" in rid or rid in seen:
            raise ProjectionError("duplicate or invalid record ID")
        seen.add(rid)
        content = record["content"]
        if not isinstance(content, str):
            raise ProjectionError("invalid canonical content")
        if len(content.encode("utf-8")) != record["content_bytes"]:
            raise ProjectionError("canonical content byte count mismatch")
        summary = {field: record[field] for field in SUMMARY_FIELDS}
        if not isinstance(summary["title"], str):
            raise ProjectionError("invalid title")
        detail = {"schema_version": 1, **summary,
                  "content": content, "path": record["path"],
                  "links": record.get("links", []),
                  "history_index": f"history/{rid}/index.json"}
        raw = json_bytes(detail)
        summary["detail_bytes"] = len(raw)
        files[f"records/{rid}.json"] = raw
        files[f"records/{rid}.meta.json"] = json_bytes({"schema_version": 1, **summary})
        summaries.append(summary)
    summaries.sort(key=lambda item: (item["title"].casefold(), item["id"]))
    pages = paginate(summaries)
    descriptors = []
    for index, page in enumerate(pages, 1):
        path = f"records/catalog/{index}.json"
        files[path] = page
        # Each page is bounded by paginate; count from its actual payload.
        import json
        descriptors.append({"number": index, "url": path,
                            "count": len(json.loads(page)["items"])})
    files["records/catalog/index.json"] = json_bytes({
        "schema_version": 1, "record_count": len(summaries), "pages": descriptors})
    return files
