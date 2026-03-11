---
id: DD-APP-API-001
title: run制御APIアプリ実装詳細
doc_type: API詳細
phase: DD
version: 1.2.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-11'
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
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-016]]'
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
4. `parent_run_id` / repair 条件がある場合は `lineage` / `repair` へ整形する。
5. `durable_execution_arn` がある場合のみ durable execution 状態を補強する。

### `POST /runs/{run_id}/repairs`
1. path の `run_id` を親run IDとして検証する。
2. request を `RepairRunCreateRequest` へパースし、初期スコープ（`phase=study1`, `scope=invalid_only`, `mode=renormalize|rerun`）を検証する。
3. 親runの状態を確認し、終端状態以外は `409` を返す。
4. 親runの `invalid/study1` と `manifests/study1` を読み、対象 invalid を `repair/seed.jsonl` へ固定化する。
5. `mode=rerun` の場合は seed 行件数を model 単位で集計し、親runの `shard_size` で `100..shard_size` に分割不能なら `409` を返す。
6. 同一親run + 同一 repair 条件の既存 child repair run がある場合は `409` を返す。
7. 新規時のみ child run の `RunConfig` と `RunStatus(QUEUED)` を保存し、durable 起動を要求する。

### `GET /runs`
1. `limit` と `next_token` を検証する。
2. DynamoDB から idempotency 行を除いた run summary を走査する。
3. `created_at` 降順へ整列し、ページング対象の run を決定する。
4. 各 run の `lineage` / `repair` メタデータを整形する。
5. 各 run の `artifact_index.json` または S3 prefix を読み、S3 状況サマリを付加する。
6. `runs[]`, `returned_count`, `total_count`, `next_token` を返す。

### `GET /runs/{run_id}/artifacts`
1. S3 の reports/normalized/invalid prefix を列挙する。
2. DynamoDB 上の `lineage` / `repair` メタデータを付加する。
3. key 一覧をソートして返す。
4. 空の場合も `200` + 空配列で返す。

## バリデーション規約
- 構文検証 -> 業務検証 -> 競合検証の順で評価する。
- 最初の失敗理由を Problem Details 相当で返す。
- 未知 `run_id` は `404` とし、内部エラー詳細は露出しない。

## 受入条件
- 4 API すべてで固定制約とエラー契約が一貫している。
- 同一 `idempotency_key` の再送で重複起動が発生しない。
- repair run で parent/child 関係と repair 条件が状態/成果物APIから把握できる。
- run 一覧APIから run_id と S3 状況が把握できる。

## 変更履歴
- 2026-03-12: repair rerun の Batch 制約検証を追加 [[DD-INF-DEP-002]]
- 2026-03-11: repair run API の受付手順と lineage/repair 整形処理を追記 [[RQ-RDR-003]]
- 2026-03-06: `GET /runs` の処理順を追加し、status の durable 補強処理を追記 [[DD-INF-API-001]]
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]制御APIのアプリ実装規約を定義） [[BD-SYS-ADR-001]]
