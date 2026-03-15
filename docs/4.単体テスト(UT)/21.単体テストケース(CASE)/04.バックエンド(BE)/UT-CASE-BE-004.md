---
id: UT-CASE-BE-004
title: GET /runs/{run_id} 状態参照
doc_type: 単体テストケース
phase: UT
version: 1.2.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-13'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-API-001]]'
related:
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-017]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `GET /runs/{run_id}`

## テスト目的
- 状態応答に必須項目が含まれることを確認する。
- 状態情報の参照元が DynamoDB 正本であることを確認する。
- repair run の場合に `lineage` / `repair` が整形されることを確認する。
- cancel 済み run の場合に `cancel` 情報と `CANCELLING/CANCELLED` 状態が整形されることを確認する。

## 手順
1. `run_control_table` に既存 `run_id` の状態を投入する。
2. `GET /runs/{run_id}` の状態取得を実行する。

## 期待結果
- `200 OK` を返す。
- `phase/state/progress/retry_count/last_error` が含まれる。
- cancel 情報が存在する場合は `cancel.requested_at/reason/requested_phase/requested_step` が含まれる。
- DynamoDB に投入した状態値と一致する。

## 変更履歴
- 2026-03-13: cancel 状態と `cancel` メタデータの応答確認を追加 [[RQ-FR-017]]
- 2026-03-11: repair run の lineage/repair 応答確認を追加 [[RQ-RDR-003]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
