# Agentic knowledge workflow

This historical design entry point is superseded by the canonical [record and write contract](../../openwiki/design/records-and-writes.md), [UI/UX contract](../../openwiki/design/ui-ux.md) and [acceptance matrix](../../openwiki/design/acceptance.md).

One record and its sibling log form one aggregate. CLI and MCP use the same atomic writer; the diary is a projection, not an independently authored journal. Multi-record link repairs produce one event per affected record with a shared operation ID. Asynchronous reconciliation, optional atomicity, source date folders and separate journal aggregates are not target alternatives.

Implementation is pending. Keep substantive design in OpenWiki; amend that contract rather than duplicating requirements here.
