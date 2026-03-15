---
id: RQ-UC-006
title: 実行を停止する
doc_type: ユースケース
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-13
updated: '2026-03-13'
up:
  - '[[RQ-SH-001]]'
related:
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-017]]'
  - '[[RQ-RDR-004]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - UC
---

## シナリオ
1. [[RQ-SH-001|管理者]]が不要になった、または異常を検知した [[RQ-GL-002|run]] に対して `POST /runs/{run_id}/cancel` を呼び出す。
2. システムが停止要求を受理し、`state=CANCELLING` を返す。
3. システムが durable execution と進行中 Batch job の停止を完了し、最終的に `state=CANCELLED` へ遷移させる。

## 受入条件
- 停止要求後に新しい Batch submit が始まらない。
- `GET /runs/{run_id}` で `CANCELLING` と `CANCELLED` が区別できる。

## 変更履歴
- 2026-03-13: 初版作成（run 停止ユースケースを追加） [[RQ-RDR-004]]
