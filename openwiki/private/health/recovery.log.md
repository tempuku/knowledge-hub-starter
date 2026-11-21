# Record history

## Entry a6eebd6a-85ef-4c7b-916d-6abd24a40238
```json
{
  "schema_version": 1,
  "id": "a6eebd6a-85ef-4c7b-916d-6abd24a40238",
  "record_id": "5b82fc58-cccd-4997-ad93-b74b07ce3640",
  "operation_id": "e9944cd9-cd27-4080-aca8-8c65b9d64208",
  "sequence": 1,
  "action": "CREATED",
  "recorded_at": "2026-11-18T18:54:09Z",
  "occurred_on": "2026-10-27",
  "occurred_at": null,
  "actor": {
    "id": "synthetic-fixture-author",
    "kind": "agent",
    "label": "Fixture Author"
  },
  "summary": "Create synthetic recovery timeline with outstanding MRI and X-ray document placeholders",
  "path_before": null,
  "path_after": "openwiki/private/health/recovery.md",
  "before": null,
  "after": "---\nid: \"5b82fc58-cccd-4997-ad93-b74b07ce3640\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline — synthetic test\"\ndescription: \"Synthetic acceptance fixture for personal priorities and document links; not a real medical record.\"\nstatus: in_progress\nvisibility: private\noccurred_on: \"2026-10-27\"\ntags: [fixture, health, recovery]\n---\n\n# Recovery timeline — synthetic test\n\n**TEST DATA ONLY.** This example is not a statement about an actual person's medical condition.\n\n- **Timeline start:** October 27, 2026.\n- **Tracking state:** In progress. It remains on the daily stand-up even without recent activity.\n- **MRI (MRT):** Placeholder — no document supplied or linked.\n- **X-ray:** Placeholder — no document supplied or linked.\n\n## Next review\n\nTrack updates, relevant milestones and protected document links here when available. Do not invent clinical findings, diagnoses, or attachments.\n",
  "before_sha256": null,
  "after_sha256": "6a3b52b7e4ae027d324346b5604bfaba56d26dc342c83f78518f158512b08a58",
  "previous_event_id": null,
  "idempotency_key": "1f05c7bc-5c61-48c8-85ca-07c78c8b414f",
  "request_sha256": "6a3b52b7e4ae027d324346b5604bfaba56d26dc342c83f78518f158512b08a58",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry 58d4b9ca-4fd8-4cd9-bf4c-29f7af7f137c
```json
{
  "schema_version": 1,
  "id": "58d4b9ca-4fd8-4cd9-bf4c-29f7af7f137c",
  "record_id": "5b82fc58-cccd-4997-ad93-b74b07ce3640",
  "operation_id": "b2397b98-8457-49ff-8ae9-acb2540a11d2",
  "sequence": 2,
  "action": "UPDATED",
  "recorded_at": "2026-11-21T21:13:09Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "opencode-agent",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Rename the generic recovery tag so public publication does not collide with private metadata",
  "path_before": "openwiki/private/health/recovery.md",
  "path_after": "openwiki/private/health/recovery.md",
  "before": "---\nid: \"5b82fc58-cccd-4997-ad93-b74b07ce3640\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline — synthetic test\"\ndescription: \"Synthetic acceptance fixture for personal priorities and document links; not a real medical record.\"\nstatus: in_progress\nvisibility: private\noccurred_on: \"2026-10-27\"\ntags: [fixture, health, recovery]\n---\n\n# Recovery timeline — synthetic test\n\n**TEST DATA ONLY.** This example is not a statement about an actual person's medical condition.\n\n- **Timeline start:** October 27, 2026.\n- **Tracking state:** In progress. It remains on the daily stand-up even without recent activity.\n- **MRI (MRT):** Placeholder — no document supplied or linked.\n- **X-ray:** Placeholder — no document supplied or linked.\n\n## Next review\n\nTrack updates, relevant milestones and protected document links here when available. Do not invent clinical findings, diagnoses, or attachments.\n",
  "after": "---\nid: \"5b82fc58-cccd-4997-ad93-b74b07ce3640\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline — synthetic test\"\ndescription: \"Synthetic acceptance fixture for personal priorities and document links; not a real medical record.\"\nstatus: in_progress\nvisibility: private\noccurred_on: \"2026-10-27\"\ntags: [fixture, health, health-recovery]\n---\n\n# Recovery timeline — synthetic test\n\n**TEST DATA ONLY.** This example is not a statement about an actual person's medical condition.\n\n- **Timeline start:** October 27, 2026.\n- **Tracking state:** In progress. It remains on the daily stand-up even without recent activity.\n- **MRI (MRT):** Placeholder — no document supplied or linked.\n- **X-ray:** Placeholder — no document supplied or linked.\n\n## Next review\n\nTrack updates, relevant milestones and protected document links here when available. Do not invent clinical findings, diagnoses, or attachments.\n",
  "before_sha256": "6a3b52b7e4ae027d324346b5604bfaba56d26dc342c83f78518f158512b08a58",
  "after_sha256": "6526f5bb4fb47955f49df1d3b16e478f73e61ca5c97ae80f8c0210f276731ccb",
  "previous_event_id": "a6eebd6a-85ef-4c7b-916d-6abd24a40238",
  "idempotency_key": "a1f519a7-e4c4-4b7e-b07b-5ef4fcdbbba0",
  "request_sha256": "6e39134088c96563877ad38c6c9f477d776476b1acc2075fb2433ea79544148d",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
