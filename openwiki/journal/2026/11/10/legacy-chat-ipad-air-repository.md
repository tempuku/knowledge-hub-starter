---
type: diary-entry
title: Published Legacy Chat iPad Air prototype and DDD knowledge base
description: Prepared and published the private iOS 12 ChatGPT-alternative prototype, DDD use cases, and OpenWiki-compatible OKF knowledge tree; native device validation remains outstanding.
occurred_on: "2026-11-10"
project: legacy-chat-ipad-air
tags: [ios12, ipad-air, legacy-chat, github, ddd, openwiki, okf, cloudflare]
status: draft
visibility: public
sources:
  - resource: https://github.com/tempuku/legacy-chat-ipad-air
    title: Legacy Chat repository (private)
  - resource: https://github.com/tempuku/legacy-chat-ipad-air/commit/f70a219eed58d3f2b7f3617fea5d7fd5e0fd4054
    title: Source publication commit and complete diff (42 files)
  - resource: https://github.com/tempuku/legacy-chat-ipad-air/blob/main/docs/ddd/use-cases.md
    title: DDD use-case catalogue
  - resource: https://github.com/tempuku/legacy-chat-ipad-air/blob/main/openwiki/index.md
    title: OpenWiki-compatible OKF v0.2 index
  - resource: https://github.com/tempuku/legacy-chat-ipad-air/blob/main/README.md
    title: Scope, setup, and verification limitations
---

# Legacy Chat on the original iPad Air

Prepared and published [`tempuku/legacy-chat-ipad-air`](https://github.com/tempuku/legacy-chat-ipad-air) as a **private GitHub repository**. Its purpose is to use a first-generation iPad Air (iOS 12) as a native text-chat client without depending on modern Safari or remote desktop.

The initial [publication commit](https://github.com/tempuku/legacy-chat-ipad-air/commit/f70a219eed58d3f2b7f3617fea5d7fd5e0fd4054) contains **42 files**, including a Swift/UIKit iOS project, a Cloudflare Worker gateway with server-side OpenAI API credentials, a local conversation store, a ChatGPT-export converter, DDD use cases and BDD scenarios, an OKF v0.2-compatible OpenWiki knowledge tree, agent contribution rules, and GitHub Actions validation workflows.

**Important boundary:** The public OpenAI API cannot directly synchronize or continue existing personal ChatGPT account threads. Imported ChatGPT exports are offline snapshots; any follow-up becomes a separate API-based conversation. ChatGPT subscription and OpenAI API billing are separate.

**Readiness:** Source and documentation are published. Prior local tests were reported as passing, but GitHub CI completion, native iOS compilation/signing, Cloudflare deployment, and testing on the physical iPad Air are **not yet verified**. Do not describe this as an installable, device-tested release.

**Next:** Check GitHub Actions, run an iOS 12 build with a compatible Xcode toolchain, deploy and verify the Worker without exposing credentials, then perform physical iPad installation and end-to-end chat tests.

**Original evidence and full diff:** [publication commit](https://github.com/tempuku/legacy-chat-ipad-air/commit/f70a219eed58d3f2b7f3617fea5d7fd5e0fd4054). This short diary record is a summary, not a replacement for the source repository.
