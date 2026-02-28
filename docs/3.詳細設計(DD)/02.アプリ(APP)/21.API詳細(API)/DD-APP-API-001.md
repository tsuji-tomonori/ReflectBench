---
id: DD-APP-API-001
title: run制御APIアプリ実装詳細
doc_type: API詳細
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-004]]'
tags:
  - llm-temp-introspection
  - DD
  - APP
  - API
---

## 詳細仕様
- API 契約は [[DD-INF-API-001]] を正本とし、本書はハンドラ内部の処理順と検証規約を定義する。
- 外部応答は `snake_case` 固定とし、内部モデルとの差分は serializer で統一変換する。
- 状態参照の正本は DynamoDB、成果物本文の正本は S3 とし、ハンドラは両者を用途別に参照する。

## ハンドラ処理
### `POST /runs`
1. request を `RunCreateRequest` へパースする。
2. 固定制約（`loops=10`, `full_cross=true`）を検証する。
3. `idempotency_key` を DynamoDB で照合し、同一条件なら既存 `run_id`、異条件なら `409` を返す。
4. 新規時のみ `RunConfig` を S3 保存し、`RunStatus(QUEUED)` を DynamoDB 作成する。
5. durable 起動を要求し、`202` 応答を返す。

### `GET /runs/{run_id}`
1. `run_id` 形式を検証する。
2. DynamoDB から `RunStatus` を取得し [[RQ-GL-003|phase]]/state/progress を整形する。
3. `last_error` は欠損時 `null` を返す。

### `GET /runs/{run_id}/artifacts`
1. S3 の reports/normalized/invalid prefix を列挙する。
2. key 一覧をソートして返す。
3. 空の場合も `200` + 空配列で返す。

## バリデーション規約
- 構文検証 -> 業務検証 -> 競合検証の順で評価する。
- 最初の失敗理由を Problem Details 相当で返す。
- 未知 `run_id` は `404` とし、内部エラー詳細は露出しない。

## 受入条件
- 3 API すべてで固定制約とエラー契約が一貫している。
- 同一 `idempotency_key` の再送で重複起動が発生しない。

## 変更履歴
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]制御APIのアプリ実装規約を定義） [[BD-SYS-ADR-001]]
