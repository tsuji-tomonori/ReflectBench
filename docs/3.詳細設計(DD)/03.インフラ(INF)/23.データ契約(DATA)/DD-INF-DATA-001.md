---
id: DD-INF-DATA-001
title: runデータ契約詳細
doc_type: データ契約
phase: DD
version: 1.2.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-06'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[RQ-FR-011]]'
  - '[[RQ-FR-013]]'
  - '[[RQ-FR-014]]'
  - '[[RQ-GL-012]]'
tags:
  - llm-temp-introspection
  - DD
  - DATA
---

## 詳細仕様
- モデル出力は strict JSON のみ受理し、Pydantic 検証成功分のみ `normalized/` へ保存する。
- 検証失敗は `invalid/` に退避し、[[RQ-GL-002|run]] 集計は除外継続する。

## 正本参照
- 本書は S3 キー命名・データ契約（schema/成果物種別）の正本とする。
- API ごとの S3 操作（どの API のどの phase でどのように CRUD するか）の正本は [[DD-INF-API-001]] を参照する。

## データ原本境界
- `RunStatus` と `idempotency_key` の正本は DynamoDB（`run_control_table`）とする。
- 実験の成果物本文（JSONL/CSV/manifest/batch-output）は S3 を正本とする。
- `GET /runs` と `GET /runs/{run_id}` は DynamoDB を参照し、`GET /runs/{run_id}/artifacts` は S3 キー契約を返す。

## [[RQ-GL-012|canonical schema]]
### `RunConfig`
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `run_id` | string | Yes | 実行ID |
| `region` | string | Yes | `ap-southeast-2` |
| `models` | string[] | Yes | 対象4モデル |
| `loops` | integer | Yes | `10` |
| `full_cross` | boolean | Yes | `true` |
| `shard_size` | integer | Yes | 初期値 `500` |
| `poll_interval_sec` | integer | Yes | 初期値 `180` |
| `created_at` | string(datetime) | Yes | UTC ISO8601 |

### `RunStatus`
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `run_id` | string | Yes | 実行ID |
| `phase` | string | Yes | 現在フェーズ |
| `state` | string | Yes | `QUEUED/RUNNING/SUCCEEDED/FAILED/PARTIAL` |
| `progress` | object | Yes | `completed_steps`,`total_steps`,`percent` |
| `retry_count` | integer | Yes | 累積 retry 回数 |
| `last_error` | object\|null | No | `step`,`reason`,`retryable` |
| `started_at` | string(datetime)\|null | No | 実行開始 |
| `finished_at` | string(datetime)\|null | No | 実行完了 |
| `execution_name` | string\|null | No | durable execution 名 |
| `durable_execution_arn` | string\|null | No | durable execution ARN |
| `artifact_index_key` | string\|null | No | 成果物索引キー |

### `RunListItem`
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `run_id` | string | Yes | 実行ID |
| `phase` | string | Yes | 現在フェーズ |
| `step` | string\|null | No | 現在 step |
| `state` | string | Yes | `QUEUED/RUNNING/SUCCEEDED/FAILED/PARTIAL` |
| `progress` | object | Yes | `completed_steps`,`total_steps`,`percent` |
| `created_at` | string(datetime)\|null | No | 受付時刻 |
| `updated_at` | string(datetime)\|null | No | 最終更新時刻 |
| `started_at` | string(datetime)\|null | No | 実行開始 |
| `finished_at` | string(datetime)\|null | No | 実行完了 |
| `execution_name` | string\|null | No | durable execution 名 |
| `durable_execution_arn` | string\|null | No | durable execution ARN |
| `s3_status` | object | Yes | S3 状況サマリ |

### `RunS3Status`
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `config_exists` | boolean | Yes | `config.json` 存在有無 |
| `artifact_index_exists` | boolean | Yes | `reports/artifact_index.json` 存在有無 |
| `reports` | object | Yes | `count`,`latest_key`,`latest_modified_at` |
| `normalized` | object | Yes | `count`,`latest_key`,`latest_modified_at` |
| `invalid` | object | Yes | `count`,`latest_key`,`latest_modified_at` |
| `batch_output` | object | Yes | `count`,`latest_key`,`latest_modified_at` |

### `RunControl`（DynamoDB保存）
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `run_id` | string | Yes | PK |
| `idempotency_key` | string | No | GSI参照キー（同値再送判定） |
| `request_hash` | string | Yes | 条件差分検知用ハッシュ |
| `phase` | string | Yes | 現在フェーズ |
| `state` | string | Yes | `QUEUED/RUNNING/SUCCEEDED/FAILED/PARTIAL` |
| `progress` | object | Yes | `completed_steps`,`total_steps`,`percent` |
| `retry_count` | integer | Yes | 累積 retry 回数 |
| `last_error` | object\|null | No | `step`,`reason`,`retryable` |
| `execution_name` | string\|null | No | durable execution 名 |
| `durable_execution_arn` | string\|null | No | durable execution ARN |
| `artifact_index_key` | string\|null | No | reports/normalized/invalid の索引キー |
| `updated_at` | string(datetime) | Yes | 最終更新時刻 |

### `Study1Record`
| フィールド | 型 | 必須 |
|---|---|---|
| `record_id` | string | Yes |
| `run_id` | string | Yes |
| `model_id` | string | Yes |
| `temperature` | number | Yes |
| `prompt_type` | string | Yes |
| `target` | string | Yes |
| `loop_index` | integer | Yes |
| `generated_sentence` | string | Yes |
| `reasoning` | string | Yes |
| `judgment` | string | Yes |

### `PredictionRecord`（Study2/A/D 共通）
| フィールド | 型 | 必須 |
|---|---|---|
| `record_id` | string | Yes |
| `run_id` | string | Yes |
| `phase` | string | Yes |
| `generator_model` | string | Yes |
| `predictor_model` | string | Yes |
| `source_record_id` | string | Yes |
| `predicted_label` | string | Yes |
| `raw_text` | string | Yes |

### `BatchInputRow`（Bedrock投入形式）
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `recordId` | string | Yes | manifest 行と再結合するための安定ID |
| `modelInput.messages` | array | Yes | Converse 入力。最低1件の user message を持つ |
| `modelInput.inferenceConfig.temperature` | number | No | Study1 は列挙温度、予測系は `0.0` |

### `BatchOutputRow`（Bedrock出力形式）
| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `recordId` | string | Yes | `BatchInputRow.recordId` を引き継ぐ |
| `modelOutput` | object | Cond | 成功時に存在。本文JSONを内包する wrapper |
| `error` | object/string | Cond | 失敗時に存在。`errorMessage` を invalid 理由に記録 |

## deterministic ID
- `record_id = sha256(run_id + phase + model + target + prompt_type + temp + loop_index)` とする。
- 再試行・再実行でも同一条件なら同一 `record_id` を生成する。

## S3 格納契約
- `runs/{run_id}/config.json`
- `runs/{run_id}/manifests/{phase}/{model}/part-xxxxx.jsonl`
- `runs/{run_id}/batch-input/{phase}/{model}/part-xxxxx.jsonl`
- `runs/{run_id}/batch-output/{phase}/{model}/...`
- `runs/{run_id}/normalized/{phase}/...jsonl`
- `runs/{run_id}/invalid/{phase}/{model}/...jsonl`
- `runs/{run_id}/reports/study1_summary.csv`
- `runs/{run_id}/reports/study2_within.csv`
- `runs/{run_id}/reports/study2_across.csv`
- `runs/{run_id}/reports/experiment_a.csv`
- `runs/{run_id}/reports/experiment_d.csv`
- `runs/{run_id}/reports/run_manifest.json`
- `runs/{run_id}/reports/artifact_index.json`

## `run_manifest.json`
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `phase_counts` | object | [[RQ-GL-003|phase]]別件数 |
| `retry_counts` | object | [[RQ-GL-003|phase]]別 retry 件数 |
| `invalid_counts` | object | [[RQ-GL-003|phase]]別 invalid 件数 |
| `excluded_reasons` | object | 集計除外理由 |
| `estimated_model_cost_usd` | number | 推定モデル費 |

## 受入条件
- `batch-input/` 行は `recordId` と `modelInput.messages` を必須とし、欠落行は submit 前に検出される。
- strict JSON + Pydantic 検証の成功/失敗で `normalized/` と `invalid/` が分離される。
- `batch-output/` は `recordId` で manifest と再結合して正規化される。
- `run_manifest.json` から [[RQ-GL-003|phase]]別件数、retry、invalid を追跡できる。
- `artifact_index.json` または prefix 集計により run 一覧APIから S3 状況を把握できる。
- 同一条件再実行で `record_id` が一致する。

## 変更履歴
- 2026-03-06: `RunListItem` / `RunS3Status` と `artifact_index.json` を追記 [[DD-INF-API-001]]
- 2026-03-02: API x phase x CRUD の正本参照先を [[DD-INF-API-001]] に明記 [[RQ-FR-004]]
- 2026-03-02: `batch-input` 契約、`modelInput.messages` 必須、`recordId` 再結合の正規化契約を追記 [[RQ-FR-006]]
- 2026-02-28: 初版作成（[[RQ-GL-012|canonical schema]] と成果物契約を定義） [[BD-SYS-ADR-001]]
