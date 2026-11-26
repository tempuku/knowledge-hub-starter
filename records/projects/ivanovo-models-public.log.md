# Record history

## Entry 1e26b8e8-cc64-46dd-923b-ea0163481012
```json
{
  "schema_version": 1,
  "id": "1e26b8e8-cc64-46dd-923b-ea0163481012",
  "record_id": "1e26b8e8-cc64-46dd-923b-ea0163480012",
  "operation_id": "1e26b8e8-cc64-46dd-923b-ea0163482012",
  "sequence": 1,
  "action": "CREATED",
  "recorded_at": "2026-11-18T19:13:33Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "public-demo-fixture",
    "kind": "agent",
    "label": "Public Demo"
  },
  "summary": "Create explicitly public demonstration record",
  "path_before": null,
  "path_after": "openwiki/projects/ivanovo-models-public.md",
  "before": null,
  "after": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: in_progress\nvisibility: public\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n",
  "before_sha256": null,
  "after_sha256": "c07f8b2e83a1a26f65174a580e5bdb7362b32c7d16daf009d894b181723ab27d",
  "previous_event_id": null,
  "idempotency_key": "1e26b8e8-cc64-46dd-923b-ea0163483012",
  "request_sha256": "48ac449d1ac3f3a042c5387be0e871a966171918423e16af57362738875c2fbc",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry 16fb991b-86f3-437b-a4c5-28b3f7af6e92
```json
{
  "schema_version": 1,
  "id": "16fb991b-86f3-437b-a4c5-28b3f7af6e92",
  "record_id": "1e26b8e8-cc64-46dd-923b-ea0163480012",
  "operation_id": "eca4ba9d-6a89-479c-af7e-5f5075f6b104",
  "sequence": 2,
  "action": "UPDATED",
  "recorded_at": "2026-11-19T18:32:58Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "chatgpt-agent",
    "kind": "agent",
    "label": "Knowledge Hub evidence links"
  },
  "summary": "Link related project record and evidence graph",
  "path_before": "openwiki/projects/ivanovo-models-public.md",
  "path_after": "openwiki/projects/ivanovo-models-public.md",
  "before": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: in_progress\nvisibility: public\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n",
  "after": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: in_progress\nvisibility: public\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n\n## Linked records and evidence\n\n- [Knowledge Hub public project overview](record:9a2f68b9-a1a9-40c6-ae1c-6224e1630011) - the parent knowledge-system project explaining shared record/log and visibility principles.\n- [This project's complete append-only history](https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/projects/ivanovo-models-public.log.md) - this public demo's own recorded changes.\n- [Knowledge Hub traceable topics and evidence traversal (#46)](https://github.com/tempuku/knowledge-hub-starter/issues/46) - public documentation for related-record discovery.\n\nNo private model sources, files or manufacturing evidence are included in this public overview. The authoritative private project may provide additional evidence only to authorized readers.\n",
  "before_sha256": "c07f8b2e83a1a26f65174a580e5bdb7362b32c7d16daf009d894b181723ab27d",
  "after_sha256": "c28e85eb7fb174507986965ded0bbaa22b420e3bffc12d044bbcbf24f064d2a3",
  "previous_event_id": "1e26b8e8-cc64-46dd-923b-ea0163481012",
  "idempotency_key": "17efbb1f-b32c-4307-a5ae-77eb403d1350",
  "request_sha256": "19bfa015bc4652d2ab6605d24bc2cec0d73326ade32e36d8934bc3a1047f47a6",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry 875164b2-8c64-4a38-b177-213abe8e5988
```json
{
  "schema_version": 1,
  "id": "875164b2-8c64-4a38-b177-213abe8e5988",
  "record_id": "1e26b8e8-cc64-46dd-923b-ea0163480012",
  "operation_id": "2fa99cce-2536-44f5-819b-77d35e006655",
  "sequence": 3,
  "action": "UPDATED",
  "recorded_at": "2026-11-21T21:39:49Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "opencode-agent",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Mark the demo private and draft so it leaves the public site",
  "path_before": "openwiki/projects/ivanovo-models-public.md",
  "path_after": "openwiki/projects/ivanovo-models-public.md",
  "before": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: in_progress\nvisibility: public\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n\n## Linked records and evidence\n\n- [Knowledge Hub public project overview](record:9a2f68b9-a1a9-40c6-ae1c-6224e1630011) - the parent knowledge-system project explaining shared record/log and visibility principles.\n- [This project's complete append-only history](https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/projects/ivanovo-models-public.log.md) - this public demo's own recorded changes.\n- [Knowledge Hub traceable topics and evidence traversal (#46)](https://github.com/tempuku/knowledge-hub-starter/issues/46) - public documentation for related-record discovery.\n\nNo private model sources, files or manufacturing evidence are included in this public overview. The authoritative private project may provide additional evidence only to authorized readers.\n",
  "after": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: draft\nvisibility: private\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n\n## Linked records and evidence\n\n- [Knowledge Hub public project overview](record:9a2f68b9-a1a9-40c6-ae1c-6224e1630011) - the parent knowledge-system project explaining shared record/log and visibility principles.\n- [This project's complete append-only history](https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/projects/ivanovo-models-public.log.md) - this public demo's own recorded changes.\n- [Knowledge Hub traceable topics and evidence traversal (#46)](https://github.com/tempuku/knowledge-hub-starter/issues/46) - public documentation for related-record discovery.\n\nNo private model sources, files or manufacturing evidence are included in this public overview. The authoritative private project may provide additional evidence only to authorized readers.\n",
  "before_sha256": "c28e85eb7fb174507986965ded0bbaa22b420e3bffc12d044bbcbf24f064d2a3",
  "after_sha256": "d6936f63b09d0d30a6e887b133315b4f988585c8de28653787e64bbfe45b8a3f",
  "previous_event_id": "16fb991b-86f3-437b-a4c5-28b3f7af6e92",
  "idempotency_key": "4d716e53-d3b9-45e3-9a6e-ae5505399aea",
  "request_sha256": "56c2a8c9471f5302f4dec9f6dcda1069c2013d4952171334156f332803757e45",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry 3484706a-0f83-43ec-a5fc-e38d2d97947f
```json
{
  "schema_version": 1,
  "id": "3484706a-0f83-43ec-a5fc-e38d2d97947f",
  "record_id": "1e26b8e8-cc64-46dd-923b-ea0163480012",
  "operation_id": "2aa5a947-db5c-4b92-926c-65a19a1fa974",
  "sequence": 4,
  "action": "MOVED",
  "recorded_at": "2026-11-26T19:00:55Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "opencode-agent",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Move Ivanovo Models (public demo) under the records bundle root",
  "path_before": "openwiki/projects/ivanovo-models-public.md",
  "path_after": "records/projects/ivanovo-models-public.md",
  "before": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: draft\nvisibility: private\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n\n## Linked records and evidence\n\n- [Knowledge Hub public project overview](record:9a2f68b9-a1a9-40c6-ae1c-6224e1630011) - the parent knowledge-system project explaining shared record/log and visibility principles.\n- [This project's complete append-only history](https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/projects/ivanovo-models-public.log.md) - this public demo's own recorded changes.\n- [Knowledge Hub traceable topics and evidence traversal (#46)](https://github.com/tempuku/knowledge-hub-starter/issues/46) - public documentation for related-record discovery.\n\nNo private model sources, files or manufacturing evidence are included in this public overview. The authoritative private project may provide additional evidence only to authorized readers.\n",
  "after": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: draft\nvisibility: private\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n\n## Linked records and evidence\n\n- [Knowledge Hub public project overview](record:9a2f68b9-a1a9-40c6-ae1c-6224e1630011) - the parent knowledge-system project explaining shared record/log and visibility principles.\n- [This project's complete append-only history](https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/projects/ivanovo-models-public.log.md) - this public demo's own recorded changes.\n- [Knowledge Hub traceable topics and evidence traversal (#46)](https://github.com/tempuku/knowledge-hub-starter/issues/46) - public documentation for related-record discovery.\n\nNo private model sources, files or manufacturing evidence are included in this public overview. The authoritative private project may provide additional evidence only to authorized readers.\n",
  "before_sha256": "d6936f63b09d0d30a6e887b133315b4f988585c8de28653787e64bbfe45b8a3f",
  "after_sha256": "d6936f63b09d0d30a6e887b133315b4f988585c8de28653787e64bbfe45b8a3f",
  "previous_event_id": "875164b2-8c64-4a38-b177-213abe8e5988",
  "idempotency_key": "ca82ad39-758d-43de-ba4f-354be6b3a2ce",
  "request_sha256": "6deb72ffd7c17920e87e59e2d3b79f7881feecb1f6eb023200b2664dd6442093",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
