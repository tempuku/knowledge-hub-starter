# OKF Record Change Log

## Entry demo-baseline-20261110
```json
{
  "id": "demo-baseline-20261110",
  "timestamp": "2026-11-10T17:38:34Z",
  "actor": "agent",
  "action": "BASELINED",
  "summary": "Registered existing diary demo as baseline for native OKF logging",
  "record": "openwiki/concepts/diary-diff-demo.md",
  "visibility": "public",
  "before": null,
  "after": "---\ntype: concept\ntitle: Diary diff demo\ndescription: A public test source for inspecting changes in the diary.\nvisibility: public\nstatus: stable\ntags: [knowledge-hub, demo, history]\n---\n\n# Diary diff demo\n\nThe revised record now has a traceable change history.\n\n- Status: updated\n- Feature: diary browsing\n- Feature: expandable full diff\n- Source: original record on GitHub\n",
  "before_sha256": null,
  "after_sha256": "2c78655757356c8510f0f633e121247ed11a9001d6dd56e78e314eec7d602533"
}
```

## Entry demo-native-update-20261110
```json
{
  "id": "demo-native-update-20261110",
  "timestamp": "2026-11-10T17:38:34Z",
  "actor": "agent",
  "action": "UPDATED",
  "summary": "Added native OKF log demonstration and diary indexing notes",
  "record": "openwiki/concepts/diary-diff-demo.md",
  "visibility": "public",
  "before": "---\ntype: concept\ntitle: Diary diff demo\ndescription: A public test source for inspecting changes in the diary.\nvisibility: public\nstatus: stable\ntags: [knowledge-hub, demo, history]\n---\n\n# Diary diff demo\n\nThe revised record now has a traceable change history.\n\n- Status: updated\n- Feature: diary browsing\n- Feature: expandable full diff\n- Source: original record on GitHub\n",
  "after": "---\ntype: concept\ntitle: Diary diff demo\ndescription: A public test source for inspecting changes in the diary.\nvisibility: public\nstatus: stable\ntags: [knowledge-hub, demo, history]\n---\n\n# Diary diff demo\n\nThe revised record now has a traceable change history.\n\n- Status: updated\n- Feature: diary browsing\n- Feature: expandable full diff\n- Source: original record on GitHub\n\n## Native OKF log demonstration\n\nThis update demonstrates a second revision recorded in the sibling append-only log.\n\n- History source: record-owned Markdown log\n- Diary grouping: timestamp date\n- Detail view: complete before and after snapshots\n",
  "before_sha256": "2c78655757356c8510f0f633e121247ed11a9001d6dd56e78e314eec7d602533",
  "after_sha256": "8f8ef83e4a8f331f31d8f217088c91f4374eca8490b619cf4c29b20bb90279e4"
}
```
