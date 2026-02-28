---
id: RQ-GL-006
title: batch invocation job
term_en: batch_invocation_job
doc_type: 用語
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related: []
tags:
  - llm-temp-introspection
  - RQ
  - GL
---

## 定義
| 項目 | 内容 |
|---|---|
| 用語ID | `RQ-GL-006` |
| 用語名 | [[RQ-GL-006|batch invocation job]] |
| 英名 | `batch_invocation_job` |
| 定義 | Bedrock `CreateModelInvocationJob` で作成される非同期推論 job。 |
| 判定条件/適用範囲 | [[RQ-GL-004|shard]] 単位で作成・監視・再試行する対象。 |

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
