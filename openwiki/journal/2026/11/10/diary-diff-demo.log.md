# OKF Record Change Log

## Entry git-75ed73b794084a44
```json
{
  "id": "git-75ed73b794084a44",
  "timestamp": "2026-11-10T16:57:01Z",
  "actor": "tempuku",
  "action": "CREATED",
  "summary": "test: add linked diary entry with real source revision diff",
  "record": "openwiki/journal/2026/11/10/diary-diff-demo.md",
  "visibility": "public",
  "before": null,
  "after": "---\ntype: diary-entry\ntitle: Demo — inspect a knowledge record update\ndescription: Updated the demo record, added diff navigation, and linked the original source.\noccurred_on: \"2026-11-10\"\nproject: knowledge-hub\ntags: [demo, change-history, diff]\nstatus: stable\nvisibility: public\nactor: test-fixture\nchange:\n  record: openwiki/concepts/diary-diff-demo.md\n  before: 655c75c1ecd8df4bfc1503e0fc1348ce92a4e27f\n  after: 4c7db76f0be69f6687daa7fbb0eb1e06401f9fd9\nsources:\n  - resource: https://github.com/tempuku/knowledge-hub-starter/blob/4c7db76f0be69f6687daa7fbb0eb1e06401f9fd9/openwiki/concepts/diary-diff-demo.md\n    title: Original demo record\n---\n\n# Change history demonstration\n\nThis is a deliberately public test record for issue #13.\n\nOpen the entry, select **View full diff**, and follow **Original record** to inspect the source. The diff is generated from two real Git commits.\n",
  "before_sha256": null,
  "after_sha256": "9241b22144bf91454200e672465bf407c316bc499735acfcbf859854c9d46d13",
  "source_commit": "75ed73b794084a4411fcc4e4c368639ed278204e",
  "provenance": "git-backfill"
}
```
