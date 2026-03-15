---
id: RQ-RDR-004
title: run停止APIとcancel状態遷移の追加
doc_type: 要求決定記録
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-13
updated: '2026-03-13'
up:
  - '[[RQ-DG-001]]'
related:
  - '[[RQ-UC-006]]'
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-017]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - RDR
---

## 決定
- 非終端 run を停止するため、`POST /runs/{run_id}/cancel` を run 制御APIに追加する。
- 停止要求の状態表現として `CANCELLING` と `CANCELLED` を追加し、通常完了との競合時は先に確定した終端状態を優先する。
- 停止処理は同期完了を待たず、停止要求受理後に durable execution と進行中 Bedrock Batch job の停止を非同期で進める。
- 停止要求時点の監査情報として `cancel_requested_at`, `cancel_reason`, `cancel_requested_phase`, `cancel_requested_step` を保持する。

## 根拠
- 現行の run 制御は開始と参照のみで、不要継続や異常 run を止める運用手段がないため。
- Bedrock Batch と durable execution の停止完了は外部サービス応答に依存するため、API 応答を同期完了にすると運用レイテンシと失敗面が増えるため。
- 中間状態なしで即 `CANCELLED` とすると、通常完了との競合時に監査・再実行判断が不明確になるため。

## 影響
- `RQ-UC-006` と `RQ-FR-017` を追加し、`GET /runs/{run_id}` の状態列挙を `CANCELLING/CANCELLED` まで拡張する。
- APP/INF 設計に cancel API / cancel worker、DynamoDB cancel メタデータ、`batch-output/*-job.json` による停止対象探索を追加する。
- 運用ランブックと UT 計画に停止要求、冪等再要求、終端 run 競合の観点を追加する。

## 変更履歴
- 2026-03-13: 初版作成（run 停止APIと cancel 状態遷移の要求決定を追加） [[RQ-RDR-004]]
