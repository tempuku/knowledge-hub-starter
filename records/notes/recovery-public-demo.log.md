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

## Entry 8d66fa43-aea0-4db5-9b7c-cab9b4e4d217
```json
{
  "schema_version": 1,
  "id": "8d66fa43-aea0-4db5-9b7c-cab9b4e4d217",
  "record_id": "8beb5eb5-b71a-4e42-897e-a6d8594b0013",
  "operation_id": "2845bd4f-aa7e-475d-9d7d-ed0462b67825",
  "sequence": 2,
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
  "path_before": "openwiki/notes/recovery-public-demo.md",
  "path_after": "openwiki/notes/recovery-public-demo.md",
  "before": "---\nid: \"8beb5eb5-b71a-4e42-897e-a6d8594b0013\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline (synthetic public demo)\"\ndescription: \"Public synthetic example to test persistent in-progress status and document placeholders.\"\nstatus: in_progress\nvisibility: public\noccurred_on: \"2026-10-27\"\ntags: [demo, fixture, health, recovery]\n---\n\n# Recovery timeline - synthetic public demo\n\n**TEST DATA ONLY.** This is not a medical claim about any person.\n\n- Timeline begins October 27, 2026.\n- Status remains In progress even after long inactivity.\n- MRI: placeholder (no file attached).\n- X-ray: placeholder (no file attached).\n\nNo real diagnosis, scan, results, or person-specific information is included.\n",
  "after": "---\nid: \"8beb5eb5-b71a-4e42-897e-a6d8594b0013\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline (synthetic public demo)\"\ndescription: \"Public synthetic example to test persistent in-progress status and document placeholders.\"\nstatus: draft\nvisibility: private\noccurred_on: \"2026-10-27\"\ntags: [demo, fixture, health, recovery]\n---\n\n# Recovery timeline - synthetic public demo\n\n**TEST DATA ONLY.** This is not a medical claim about any person.\n\n- Timeline begins October 27, 2026.\n- Status remains In progress even after long inactivity.\n- MRI: placeholder (no file attached).\n- X-ray: placeholder (no file attached).\n\nNo real diagnosis, scan, results, or person-specific information is included.\n",
  "before_sha256": "08acd144b7227348e7f2bdb5d6f58d939f51ea5d094bb21495fb3c24e29b4c5f",
  "after_sha256": "7676bf9b54e54091f7b004d4ac030e8b08a21ef073352d93a1606e281346e374",
  "previous_event_id": "8beb5eb5-b71a-4e42-897e-a6d8594b1013",
  "idempotency_key": "3e7d535a-6a6e-4543-a86a-088955cf310e",
  "request_sha256": "56c2a8c9471f5302f4dec9f6dcda1069c2013d4952171334156f332803757e45",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry 7fc2bf4c-b3c7-432f-a34c-9a67520df86c
```json
{
  "schema_version": 1,
  "id": "7fc2bf4c-b3c7-432f-a34c-9a67520df86c",
  "record_id": "8beb5eb5-b71a-4e42-897e-a6d8594b0013",
  "operation_id": "286ecb55-d816-4a08-ad66-5be421c688a4",
  "sequence": 3,
  "action": "MOVED",
  "recorded_at": "2026-11-26T18:59:33Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "opencode-agent",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Move Recovery timeline (synthetic public demo) under the records bundle root",
  "path_before": "openwiki/notes/recovery-public-demo.md",
  "path_after": "records/notes/recovery-public-demo.md",
  "before": "---\nid: \"8beb5eb5-b71a-4e42-897e-a6d8594b0013\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline (synthetic public demo)\"\ndescription: \"Public synthetic example to test persistent in-progress status and document placeholders.\"\nstatus: draft\nvisibility: private\noccurred_on: \"2026-10-27\"\ntags: [demo, fixture, health, recovery]\n---\n\n# Recovery timeline - synthetic public demo\n\n**TEST DATA ONLY.** This is not a medical claim about any person.\n\n- Timeline begins October 27, 2026.\n- Status remains In progress even after long inactivity.\n- MRI: placeholder (no file attached).\n- X-ray: placeholder (no file attached).\n\nNo real diagnosis, scan, results, or person-specific information is included.\n",
  "after": "---\nid: \"8beb5eb5-b71a-4e42-897e-a6d8594b0013\"\nschema_version: 1\ntype: note\ntitle: \"Recovery timeline (synthetic public demo)\"\ndescription: \"Public synthetic example to test persistent in-progress status and document placeholders.\"\nstatus: draft\nvisibility: private\noccurred_on: \"2026-10-27\"\ntags: [demo, fixture, health, recovery]\n---\n\n# Recovery timeline - synthetic public demo\n\n**TEST DATA ONLY.** This is not a medical claim about any person.\n\n- Timeline begins October 27, 2026.\n- Status remains In progress even after long inactivity.\n- MRI: placeholder (no file attached).\n- X-ray: placeholder (no file attached).\n\nNo real diagnosis, scan, results, or person-specific information is included.\n",
  "before_sha256": "7676bf9b54e54091f7b004d4ac030e8b08a21ef073352d93a1606e281346e374",
  "after_sha256": "7676bf9b54e54091f7b004d4ac030e8b08a21ef073352d93a1606e281346e374",
  "previous_event_id": "8d66fa43-aea0-4db5-9b7c-cab9b4e4d217",
  "idempotency_key": "018bcea0-3f92-48be-935a-4b024b01f8e7",
  "request_sha256": "3a9696fc26bce688d302e4093f0c6c58628e986f302f5a8f428c7a55e3b2479b",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
