# Record history

## Entry 8beb5eb5-b71a-4e42-897e-a6d8594b1013
```json
{
  "schema_version": 1,
  "id": "8beb5eb5-b71a-4e42-897e-a6d8594b1013",
  "record_id": "8beb5eb5-b71a-4e42-897e-a6d8594b0013",
  "operation_id": "8beb5eb5-b71a-4e42-897e-a6d8594b2013",
  "sequence": 1,
  "action": "CREATED",
  "recorded_at": "2026-11-18T19:13:33Z",
  "occurred_on": "2026-10-27",
  "occurred_at": null,
  "actor": {
    "id": "public-demo-fixture",
    "kind": "agent",
    "label": "Public Demo"
  },
  "summary": "Create explicitly public demonstration record",
  "path_before": null,
  "path_after": "openwiki/notes/recovery-public-demo.md",
  "before": null,
  "after": "---\nid: \"8beb5eb5-b71a-4e42-897e-a6d8594b0013\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline (synthetic public demo)\"\ndescription: \"Public synthetic example to test persistent in-progress status and document placeholders.\"\nstatus: in_progress\nvisibility: public\noccurred_on: \"2026-10-27\"\ntags: [demo, fixture, health, recovery]\n---\n\n# Recovery timeline - synthetic public demo\n\n**TEST DATA ONLY.** This is not a medical claim about any person.\n\n- Timeline begins October 27, 2026.\n- Status remains In progress even after long inactivity.\n- MRI: placeholder (no file attached).\n- X-ray: placeholder (no file attached).\n\nNo real diagnosis, scan, results, or person-specific information is included.\n",
  "before_sha256": null,
  "after_sha256": "08acd144b7227348e7f2bdb5d6f58d939f51ea5d094bb21495fb3c24e29b4c5f",
  "previous_event_id": null,
  "idempotency_key": "8beb5eb5-b71a-4e42-897e-a6d8594b3013",
  "request_sha256": "8ea1f61fd0de06f116610585cac68030633ceb39148af738686267105761bbc1",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry ed8d8b08-aaca-4c71-922e-d133e4f61d69
```json
{
  "schema_version": 1,
  "id": "ed8d8b08-aaca-4c71-922e-d133e4f61d69",
  "record_id": "8beb5eb5-b71a-4e42-897e-a6d8594b0013",
  "operation_id": "8dba4fae-72fe-46c7-b8f6-6a638b4565b6",
  "sequence": 2,
  "action": "UPDATED",
  "recorded_at": "2026-11-21T21:26:44Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "opencode-agent",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Complete the synthetic recovery demo",
  "path_before": "openwiki/notes/recovery-public-demo.md",
  "path_after": "openwiki/notes/recovery-public-demo.md",
  "before": "---\nid: \"8beb5eb5-b71a-4e42-897e-a6d8594b0013\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline (synthetic public demo)\"\ndescription: \"Public synthetic example to test persistent in-progress status and document placeholders.\"\nstatus: in_progress\nvisibility: public\noccurred_on: \"2026-10-27\"\ntags: [demo, fixture, health, recovery]\n---\n\n# Recovery timeline - synthetic public demo\n\n**TEST DATA ONLY.** This is not a medical claim about any person.\n\n- Timeline begins October 27, 2026.\n- Status remains In progress even after long inactivity.\n- MRI: placeholder (no file attached).\n- X-ray: placeholder (no file attached).\n\nNo real diagnosis, scan, results, or person-specific information is included.\n",
  "after": "---\nid: \"8beb5eb5-b71a-4e42-897e-a6d8594b0013\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline (synthetic public demo)\"\ndescription: \"Public synthetic example to test persistent in-progress status and document placeholders.\"\nstatus: completed\nvisibility: public\noccurred_on: \"2026-10-27\"\ntags: [demo, fixture, health, recovery]\n---\n\n# Recovery timeline - synthetic public demo\n\n**TEST DATA ONLY.** This is not a medical claim about any person.\n\n- Timeline begins October 27, 2026.\n- Status remains In progress even after long inactivity.\n- MRI: placeholder (no file attached).\n- X-ray: placeholder (no file attached).\n\nNo real diagnosis, scan, results, or person-specific information is included.\n",
  "before_sha256": "08acd144b7227348e7f2bdb5d6f58d939f51ea5d094bb21495fb3c24e29b4c5f",
  "after_sha256": "980e2a34ac42e6fd4bc6c0d3744bfaa35ee1229b43d393b5d37f8ccdbe315b64",
  "previous_event_id": "8beb5eb5-b71a-4e42-897e-a6d8594b1013",
  "idempotency_key": "a9ea8ca2-054a-42f7-9dd6-4ffac3d1b14b",
  "request_sha256": "171c109367396ac13dca9b882667042a7433acac4ffdbb87041010150289cdff",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
