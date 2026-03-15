---
id: RQ-FR-020
title: run結果APIで正規化済み実験結果を取得できる
doc_type: 機能要求
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-14
updated: '2026-03-14'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-007]]'
related:
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-018]]'
  - '[[RQ-RDR-005]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-020
- 種別: 機能要求
- 優先度: MUST
- 要求: `GET /runs/{run_id}/results` で、DynamoDB canonical result から正規化済み実験結果を取得できる。
- 要求（検索条件）: `phase`, `experiment_id`, `limit`, `next_token` で絞り込みとページングができる。
- 根拠: 解析系の入力を S3 artifact 走査ではなく、正規化済み result store から安定取得するため。
- 受入基準: 応答に `experiment_id`, `run_id`, prompt, normalized result, source metadata が含まれる。
- 例外/エラー: 未知 `run_id` は `404`、不正 query は `400` を返す。
- 依存・関連: [[RQ-UC-007]]

## 変更履歴
- 2026-03-14: 初版作成（run 結果 API を追加） [[RQ-RDR-005]]
