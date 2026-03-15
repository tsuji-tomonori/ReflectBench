---
id: DD-INF-API-001
title: run制御API詳細
doc_type: API詳細
phase: DD
version: 1.5.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-14'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-004]]'
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-016]]'
  - '[[RQ-FR-017]]'
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-019]]'
  - '[[RQ-FR-020]]'
tags:
  - llm-temp-introspection
  - DD
  - API
---

## 詳細仕様
- 対象APIは `POST /runs`, `POST /runs/{run_id}/cancel`, `POST /runs/{run_id}/repairs`, `GET /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/results`, `GET /runs/{run_id}/artifacts` の7本とする。
- 外部契約キーは `snake_case` を正本とし、内部実装の命名差は変換層で吸収する。
- `GET /runs/{run_id}` と `GET /runs/{run_id}/results` の正本データは DynamoDB、raw artifact / report の正本は S3 とする。
- `GET /runs` は運用向け一覧APIとし、DynamoDB の run summary と S3 prefix 集計を重ねて返す。
- `POST /runs/{run_id}/cancel` は停止要求の受理APIであり、durable execution 停止と Bedrock Batch 停止の完了は非同期に進む。
- report 生成は DynamoDB canonical result を参照し、S3 `normalized/` は監査用 mirror として扱う。

## エンドポイント一覧
| メソッド | パス | 役割 | 正常応答 |
|---|---|---|---|
| `POST` | `/runs` | [[RQ-GL-002|run]] 作成と durable 起動 | `202 Accepted` |
| `POST` | `/runs/{run_id}/cancel` | 非終端 [[RQ-GL-002|run]] の停止要求受理 | `202 Accepted` / `200 OK` |
| `POST` | `/runs/{run_id}/repairs` | child repair run 作成と durable 起動 | `202 Accepted` |
| `GET` | `/runs` | run 一覧と S3 状況サマリ取得 | `200 OK` |
| `GET` | `/runs/{run_id}` | [[RQ-GL-002|run]] 状態取得 | `200 OK` |
| `GET` | `/runs/{run_id}/results` | DynamoDB canonical result 取得 | `200 OK` |
| `GET` | `/runs/{run_id}/artifacts` | 成果物キー一覧取得 | `200 OK` |

## `POST /runs`
### request body
| キー | 型 | 必須 | 初期値/制約 |
|---|---|---|---|
| `loops` | integer | Yes | `10` 固定 |
| `full_cross` | boolean | Yes | `true` 固定 |
| `shard_size` | integer | No | `500`（100以上。Batch投入時は `100..shard_size` へ再配分） |
| `poll_interval_sec` | integer | No | `180` |
| `editor_model` | string | No | `apac.amazon.nova-micro-v1:0` |
| `idempotency_key` | string | No | 同値再送時に同一 `run_id` を返す |

### response body (`202`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `accepted_at` | string(datetime) | 受付時刻（UTC ISO8601） |
| `phase` | string | `STUDY1` |
| `step` | string | `STUDY1_ENUMERATE` |
| `state` | string | `QUEUED` |
| `execution_name` | string | durable execution 名（`run_id` と同値） |
| `durable_execution_arn` | string\|null | durable execution ARN |

## `POST /runs/{run_id}/cancel`
### request body
| キー | 型 | 必須 | 初期値/制約 |
|---|---|---|---|
| `reason` | string | No | 500文字以下。監査用の停止理由 |

### response body (`202` or `200`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `phase` | string | 停止要求時点のフェーズ |
| `step` | string\|null | 停止要求時点の step |
| `state` | string | `CANCELLING` または `CANCELLED` |
| `execution_name` | string\|null | durable execution 名 |
| `durable_execution_arn` | string\|null | durable execution ARN |
| `cancel` | object | `requested_at`, `reason`, `requested_phase`, `requested_step` |

### 補足
- `QUEUED/RUNNING` への初回停止要求は `202 Accepted` を返す。
- `CANCELLING/CANCELLED` への再要求は冪等成功として `200 OK` を返す。
- `SUCCEEDED/FAILED/PARTIAL` は `409 Conflict` を返す。

## `POST /runs/{run_id}/repairs`
### request body
| キー | 型 | 必須 | 初期値/制約 |
|---|---|---|---|
| `phase` | string | Yes | `study1` 固定 |
| `scope` | string | Yes | `invalid_only` 固定 |
| `mode` | string | Yes | `renormalize` or `rerun`（`rerun` は model 単位件数が Batch の `100..shard_size` を満たすこと） |
| `models` | string[] | No | 対象 invalid を model 単位で絞り込む |
| `record_ids` | string[] | No | 対象 invalid を record 単位で絞り込む |
| `rebuild_downstream` | boolean | No | `false` |

### response body (`202`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | child repair run ID |
| `accepted_at` | string(datetime) | 受付時刻（UTC ISO8601） |
| `phase` | string | `STUDY1` |
| `step` | string | `STUDY1_ENUMERATE` |
| `state` | string | `QUEUED` |
| `execution_name` | string | durable execution 名 |
| `durable_execution_arn` | string\|null | durable execution ARN |
| `lineage.parent_run_id` | string | 親run ID |
| `repair.phase` | string | `study1` |
| `repair.scope` | string | `invalid_only` |
| `repair.mode` | string | `renormalize` or `rerun` |
| `repair.rebuild_downstream` | boolean | 下流再構築有無 |
| `repair.source_invalid_keys` | string[] | 採用した parent invalid キー |

## `GET /runs`
### query string
| キー | 型 | 必須 | 初期値/制約 |
|---|---|---|---|
| `limit` | integer | No | `20`（1以上100以下） |
| `next_token` | string | No | 前回応答の継続トークン |

### response body (`200`)
| キー | 型 | 内容 |
|---|---|---|
| `runs` | object[] | run 一覧 |
| `returned_count` | integer | 今回返却件数 |
| `total_count` | integer | フィルタ後総件数 |
| `next_token` | string\|null | 続き取得用トークン |

### `runs[]`
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `phase` | string | 現在フェーズ |
| `step` | string\|null | 現在 step |
| `state` | string | `QUEUED/RUNNING/CANCELLING/CANCELLED/SUCCEEDED/FAILED/PARTIAL` |
| `progress` | object | `completed_steps`, `total_steps`, `percent` |
| `created_at` | string(datetime)\|null | 受付時刻 |
| `updated_at` | string(datetime)\|null | 最終更新時刻 |
| `started_at` | string(datetime)\|null | 実行開始時刻 |
| `finished_at` | string(datetime)\|null | 実行完了時刻 |
| `execution_name` | string\|null | durable execution 名 |
| `durable_execution_arn` | string\|null | durable execution ARN |
| `lineage` | object\|null | `parent_run_id` |
| `repair` | object\|null | repair 条件と `source_invalid_keys` |
| `cancel` | object\|null | `requested_at`, `reason`, `requested_phase`, `requested_step` |
| `s3_status` | object | S3 保存状況サマリ |

### `s3_status`
| キー | 型 | 内容 |
|---|---|---|
| `config_exists` | boolean | `config.json` の存在有無 |
| `artifact_index_exists` | boolean | `reports/artifact_index.json` の存在有無 |
| `reports` | object | `count`, `latest_key`, `latest_modified_at` |
| `normalized` | object | `count`, `latest_key`, `latest_modified_at` |
| `invalid` | object | `count`, `latest_key`, `latest_modified_at` |
| `batch_output` | object | `count`, `latest_key`, `latest_modified_at` |

## `GET /runs/{run_id}`
### response body (`200`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `phase` | string | 現在フェーズ |
| `step` | string\|null | 現在 step |
| `state` | string | `QUEUED/RUNNING/CANCELLING/CANCELLED/SUCCEEDED/FAILED/PARTIAL` |
| `progress` | object | `completed_steps`, `total_steps`, `percent` |
| `retry_count` | integer | 累積 retry 回数 |
| `last_error` | object\|null | 直近エラー（`step`,`reason`,`retryable`） |
| `started_at` | string(datetime)\|null | 実行開始時刻 |
| `finished_at` | string(datetime)\|null | 実行完了時刻 |
| `execution_name` | string\|null | durable execution 名 |
| `durable_execution_arn` | string\|null | durable execution ARN |
| `artifact_index_key` | string\|null | S3 成果物索引キー |
| `lineage` | object\|null | `parent_run_id` |
| `repair` | object\|null | repair 条件と `source_invalid_keys` |
| `cancel` | object\|null | `requested_at`, `reason`, `requested_phase`, `requested_step` |

## `GET /runs/{run_id}/results`
### query string
| キー | 型 | 必須 | 初期値/制約 |
|---|---|---|---|
| `phase` | string | No | `study1/study2_within/study2_across/experiment_a/experiment_d` |
| `experiment_id` | string | No | deterministic result ID の完全一致 |
| `limit` | integer | No | `500`（1以上1000以下） |
| `next_token` | string | No | 前回応答の継続トークン |

### response body (`200`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `results` | object[] | canonical result 一覧 |
| `returned_count` | integer | 今回返却件数 |
| `next_token` | string\|null | 続き取得用トークン |

### `results[]`
| キー | 型 | 内容 |
|---|---|---|
| `experiment_id` | string | deterministic result ID |
| `record_id` | string | 互換用。`experiment_id` と同値 |
| `phase` | string | 結果の所属 phase |
| `condition_type` | string\|null | `self_reflection/within_model/across_model/blind/wrong_label/info_plus/info_minus` |
| `models` | object | `generator_model`, `predictor_model`, `editor_model` |
| `prompt` | object | `messages`, `inference_config` |
| `normalized_result` | object | schema 検証済み結果 |
| `source` | object | `acquired_via`, `source_artifact_key`, `source_run_id`, `completed_at` |
| `metadata` | object | `target`, `prompt_type`, `temperature`, `loop_index`, `source_record_id` |

## `GET /runs/{run_id}/artifacts`
### response body (`200`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `reports` | string[] | CSV/[[RQ-GL-005|manifest]]キー一覧 |
| `normalized` | string[] | 正規化データキー一覧 |
| `invalid` | string[] | 検証失敗データキー一覧 |
| `lineage` | object\|null | `parent_run_id` |
| `repair` | object\|null | repair 条件と `source_invalid_keys` |

- 返却されるキーは S3 上の成果物を指し、実データDLは S3（または署名URL）経由とする。
- canonical な正規化済み結果の取得は `GET /runs/{run_id}/results` を用い、artifacts API は raw / report / audit artifact の列挙に限定する。

## S3 IF（API x phase x ファイルCRUD）
### CRUD定義
- `C`: `PutObject` による新規作成（同一キー再実行時は実質上書き）
- `R`: `GetObject` / `ListObjectsV2` による参照
- `U`: 同一キーへの `PutObject` 上書き更新
- `D`: 削除（本実装では未使用）

### 公開API単位
| API | phase | C | R | U | D | 対象キー / Prefix | 動作 |
|---|---|---:|---:|---:|---:|---|---|
| `POST /runs` | `STUDY1_ENUMERATE` 初期化前 | 1 | 0 | 0 | 0 | `runs/{run_id}/config.json` | run設定を保存し、durable実行を起動 |
| `POST /runs/{run_id}/cancel` | N/A | 0 | 1 | 1 | 0 | `runs/{run_id}/batch-output/` | Batch job メタデータを読み、停止要求済みステータスへ更新する |
| `POST /runs/{run_id}/repairs` | `STUDY1_ENUMERATE` 初期化前 | 2 | 1 | 0 | 0 | `runs/{repair_run_id}/config.json`, `runs/{repair_run_id}/repair/seed.jsonl`, `runs/{parent_run_id}/invalid/study1/`, `runs/{parent_run_id}/manifests/study1/` | repair対象を固定化し、child repair run を起動 |
| `GET /runs` | N/A | 0 | 1 | 0 | 0 | `runs/{run_id}/config.json`, `runs/{run_id}/reports/`, `runs/{run_id}/normalized/`, `runs/{run_id}/invalid/`, `runs/{run_id}/batch-output/` | run 一覧に対する S3 状況サマリを返却 |
| `GET /runs/{run_id}` | N/A | 0 | 0 | 0 | 0 | なし（S3不使用） | DynamoDB の `RunStatus` のみ参照 |
| `GET /runs/{run_id}/results` | N/A | 0 | 0 | 0 | 0 | なし（S3不使用） | DynamoDB canonical result を返却 |
| `GET /runs/{run_id}/artifacts` | N/A | 0 | 1 | 0 | 0 | `runs/{run_id}/config.json`, `runs/{run_id}/reports/`, `runs/{run_id}/normalized/`, `runs/{run_id}/invalid/` | run存在確認後に raw / report artifact キー一覧を返却 |

### `POST /runs` 起動後の Orchestrator phase 単位
| phase | C | R | U | D | 主なS3キー / Prefix | 処理内容 |
|---|---:|---:|---:|---:|---|---|
| `STUDY1_ENUMERATE` | 1 | 0 | 0 | 0 | `runs/{run_id}/manifests/study1/{model}/part-xxxxx.jsonl` | Study1入力manifest生成 |
| `STUDY1_BATCH_SUBMIT` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/study1/`, `runs/{run_id}/batch-input/study1/`, `runs/{run_id}/batch-output/study1/*-job.json` | manifest読込 -> Bedrock入力変換 -> jobメタ保存 |
| `STUDY1_BATCH_POLL` | 0 | 1 | 1 | 0 | `runs/{run_id}/batch-output/study1/*-job.json` | job状態参照、完了時メタ更新 |
| `STUDY1_NORMALIZE` | 1 | 1 | 0 | 0 | `runs/{run_id}/batch-output/study1/*.jsonl`, `runs/{run_id}/normalized/study1/*.jsonl`, `runs/{run_id}/invalid/study1/{model}/invalid.jsonl` | 出力正規化と不正行退避。成功分は canonical result 投入候補を生成 |
| `STUDY2_PREPARE` | 1 | 1 | 0 | 0 | `runs/{run_id}/normalized/study1/`, `runs/{run_id}/manifests/study2_within/`, `runs/{run_id}/manifests/study2_across/`, `runs/{run_id}/manifests/experiment_a_edit/`, `runs/{run_id}/manifests/experiment_d_blind/`, `runs/{run_id}/manifests/experiment_d_wrong_label/` | 下流phase向けmanifest生成 |
| `STUDY2_WITHIN` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/study2_within/`, `runs/{run_id}/batch-input/study2_within/`, `runs/{run_id}/batch-output/study2_within/`, `runs/{run_id}/normalized/study2_within/`, `runs/{run_id}/invalid/study2_within/` | submit/poll/normalize実行。成功分は canonical result へ upsert し、不足分は direct rerun 対象へ回す |
| `STUDY2_ACROSS` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/study2_across/`, `runs/{run_id}/batch-input/study2_across/`, `runs/{run_id}/batch-output/study2_across/`, `runs/{run_id}/normalized/study2_across/`, `runs/{run_id}/invalid/study2_across/` | submit/poll/normalize実行。成功分は canonical result へ upsert し、不足分は direct rerun 対象へ回す |
| `EXPERIMENT_A` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/experiment_a_edit/`, `runs/{run_id}/normalized/experiment_a_edit/`, `runs/{run_id}/manifests/experiment_a_predict/`, `runs/{run_id}/batch-input/experiment_a_predict/`, `runs/{run_id}/batch-output/experiment_a_predict/`, `runs/{run_id}/normalized/experiment_a/results.jsonl`, `runs/{run_id}/invalid/experiment_a/` | edit -> predict -> 正規化。成功分は canonical result へ upsert し、不足分は direct rerun 対象へ回す |
| `EXPERIMENT_D` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/experiment_d_blind/`, `runs/{run_id}/manifests/experiment_d_wrong_label/`, `runs/{run_id}/manifests/experiment_d_predict/`, `runs/{run_id}/batch-input/experiment_d_predict/`, `runs/{run_id}/batch-output/experiment_d_predict/`, `runs/{run_id}/normalized/experiment_d/results.jsonl`, `runs/{run_id}/invalid/experiment_d/` | blind/wrong-label -> predict -> 正規化。成功分は canonical result へ upsert し、不足分は direct rerun 対象へ回す |
| `REPORT` | 1 | 0 | 0 | 0 | `runs/{run_id}/reports/study1_summary.csv`, `runs/{run_id}/reports/study2_within.csv`, `runs/{run_id}/reports/study2_across.csv`, `runs/{run_id}/reports/experiment_a.csv`, `runs/{run_id}/reports/experiment_d.csv`, `runs/{run_id}/reports/run_manifest.json`, `runs/{run_id}/reports/artifact_index.json` | DynamoDB canonical result を読込んでレポート出力 |

### 補足
- `D`（`DeleteObject`）は未使用。
- `U` は `*-job.json` など同一キーへの再書込を指す。
- `GET /runs/{run_id}/artifacts` は成果物本文ではなくキー一覧を返す。

## エラー契約
- `400 Bad Request`: 入力不正（必須不足、制約違反、`limit` / `next_token` 不正を含む）
- `404 Not Found`: 未知 `run_id`
- `409 Conflict`: 重複起動拒否（同一 `idempotency_key` が異条件、repair の親run未終端、対象 invalid 不在、重複 repair 要求、repair rerun 件数が Batch 制約に不適合、または cancel 対象が `SUCCEEDED/FAILED/PARTIAL`）
- `500 Internal Server Error`: durable 起動失敗や状態取得失敗

## 状態遷移
`QUEUED -> RUNNING -> SUCCEEDED|FAILED|PARTIAL`

`QUEUED|RUNNING -> CANCELLING -> CANCELLED`

- `PARTIAL` は backfill 後も期待 `experiment_id` が不足したまま主要レポートを出力した状態を示す。
- `CANCELLING` は停止要求受理済みだが durable execution / Bedrock Batch 停止の完了待ちであることを示す。
- `CANCELLED` は停止要求が完了し、以後新規 submit を行わない終端状態を示す。
- 停止要求が通常完了と競合し、run が先に `SUCCEEDED/PARTIAL/FAILED` へ到達した場合は、その終端状態を優先する。

## 受入条件
- `POST /runs` が `202` と `run_id` を返し、`config.json` 保存済みである。
- `POST /runs/{run_id}/cancel` が非終端 run に対して `CANCELLING` を返し、再要求時に冪等応答できる。
- `GET /runs` で run 一覧、継続トークン、run ごとの S3 状況サマリが取得できる。
- `GET /runs/{run_id}` で [[RQ-GL-003|phase]]/state/progress/last_error が取得できる。
- `GET /runs/{run_id}/results` で canonical な正規化済み実験結果が DynamoDB から取得できる。
- `GET /runs/{run_id}/artifacts` に 5 CSV + `run_manifest.json` が含まれる。

## 変更履歴
- 2026-03-14: `GET /runs/{run_id}/results` と canonical result / backfill 前提の状態定義を追加 [[RQ-RDR-005]]
- 2026-03-13: `POST /runs/{run_id}/cancel`、`CANCELLING/CANCELLED` 状態、cancel メタデータ契約を追加 [[RQ-FR-017]]
- 2026-03-12: Bedrock Batch shard の再配分条件と repair rerun 件数制約を追記 [[DD-INF-DEP-002]]
- 2026-03-11: `POST /runs/{run_id}/repairs` と lineage/repair 応答項目を追加 [[RQ-RDR-003]]
- 2026-03-06: `GET /runs` を追加し、run 一覧 + S3 状況サマリの契約を追記 [[DD-INF-DEP-001]]
- 2026-03-02: S3 IF（API x phase x CRUD）を追記し、APIごとのS3ファイル操作境界を明記 [[RQ-FR-004]]
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]制御APIの入出力契約を定義） [[BD-SYS-ADR-001]]
