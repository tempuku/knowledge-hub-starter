---
type: diary-entry
title: Demo — inspect a knowledge record update
description: Updated the demo record, added diff navigation, and linked the original source.
occurred_on: "2026-11-10"
project: knowledge-hub
tags: [demo, change-history, diff]
status: stable
visibility: public
actor: test-fixture
change:
  record: openwiki/concepts/diary-diff-demo.md
  before: 655c75c1ecd8df4bfc1503e0fc1348ce92a4e27f
  after: 4c7db76f0be69f6687daa7fbb0eb1e06401f9fd9
sources:
  - resource: https://github.com/tempuku/knowledge-hub-starter/blob/4c7db76f0be69f6687daa7fbb0eb1e06401f9fd9/openwiki/concepts/diary-diff-demo.md
    title: Original demo record
---

# Change history demonstration

This is a deliberately public test record for issue #13.

Open the entry, select **View full diff**, and follow **Original record** to inspect the source. The diff is generated from two real Git commits.
