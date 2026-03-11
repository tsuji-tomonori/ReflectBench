---
id: DD-INF-API-001
title: run制御API詳細
doc_type: API詳細
phase: DD
version: 1.3.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-11'
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
tags:
  - llm-temp-introspection
  - DD
  - API
---

## 詳細仕様
- 対象APIは `POST /runs`, `POST /runs/{run_id}/repairs`, `GET /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/artifacts` の5本とする。
- 外部契約キーは `snake_case` を正本とし、内部実装の命名差は変換層で吸収する。
- `GET /runs/{run_id}` の正本データは DynamoDB、成果物本体の正本は S3 とする。
- `GET /runs` は運用向け一覧APIとし、DynamoDB の run summary と S3 prefix 集計を重ねて返す。

## エンドポイント一覧
| メソッド | パス | 役割 | 正常応答 |
|---|---|---|---|
| `POST` | `/runs` | [[RQ-GL-002|run]] 作成と durable 起動 | `202 Accepted` |
| `POST` | `/runs/{run_id}/repairs` | child repair run 作成と durable 起動 | `202 Accepted` |
| `GET` | `/runs` | run 一覧と S3 状況サマリ取得 | `200 OK` |
| `GET` | `/runs/{run_id}` | [[RQ-GL-002|run]] 状態取得 | `200 OK` |
| `GET` | `/runs/{run_id}/artifacts` | 成果物キー一覧取得 | `200 OK` |

## `POST /runs`
### request body
| キー | 型 | 必須 | 初期値/制約 |
|---|---|---|---|
| `loops` | integer | Yes | `10` 固定 |
| `full_cross` | boolean | Yes | `true` 固定 |
| `shard_size` | integer | No | `500`（100以上） |
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

## `POST /runs/{run_id}/repairs`
### request body
| キー | 型 | 必須 | 初期値/制約 |
|---|---|---|---|
| `phase` | string | Yes | `study1` 固定 |
| `scope` | string | Yes | `invalid_only` 固定 |
| `mode` | string | Yes | `renormalize` or `rerun` |
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
| `state` | string | `QUEUED/RUNNING/SUCCEEDED/FAILED/PARTIAL` |
| `progress` | object | `completed_steps`, `total_steps`, `percent` |
| `created_at` | string(datetime)\|null | 受付時刻 |
| `updated_at` | string(datetime)\|null | 最終更新時刻 |
| `started_at` | string(datetime)\|null | 実行開始時刻 |
| `finished_at` | string(datetime)\|null | 実行完了時刻 |
| `execution_name` | string\|null | durable execution 名 |
| `durable_execution_arn` | string\|null | durable execution ARN |
| `lineage` | object\|null | `parent_run_id` |
| `repair` | object\|null | repair 条件と `source_invalid_keys` |
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
| `state` | string | `QUEUED/RUNNING/SUCCEEDED/FAILED/PARTIAL` |
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
- DynamoDB は `RunStatus` と成果物ポインタ管理に限定し、CSV/JSONL本文は保持しない。

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
| `POST /runs/{run_id}/repairs` | `STUDY1_ENUMERATE` 初期化前 | 2 | 1 | 0 | 0 | `runs/{repair_run_id}/config.json`, `runs/{repair_run_id}/repair/seed.jsonl`, `runs/{parent_run_id}/invalid/study1/`, `runs/{parent_run_id}/manifests/study1/` | repair対象を固定化し、child repair run を起動 |
| `GET /runs` | N/A | 0 | 1 | 0 | 0 | `runs/{run_id}/config.json`, `runs/{run_id}/reports/`, `runs/{run_id}/normalized/`, `runs/{run_id}/invalid/`, `runs/{run_id}/batch-output/` | run 一覧に対する S3 状況サマリを返却 |
| `GET /runs/{run_id}` | N/A | 0 | 0 | 0 | 0 | なし（S3不使用） | DynamoDB の `RunStatus` のみ参照 |
| `GET /runs/{run_id}/artifacts` | N/A | 0 | 1 | 0 | 0 | `runs/{run_id}/config.json`, `runs/{run_id}/reports/`, `runs/{run_id}/normalized/`, `runs/{run_id}/invalid/` | run存在確認後に成果物キー一覧を返却 |

### `POST /runs` 起動後の Orchestrator phase 単位
| phase | C | R | U | D | 主なS3キー / Prefix | 処理内容 |
|---|---:|---:|---:|---:|---|---|
| `STUDY1_ENUMERATE` | 1 | 0 | 0 | 0 | `runs/{run_id}/manifests/study1/{model}/part-xxxxx.jsonl` | Study1入力manifest生成 |
| `STUDY1_BATCH_SUBMIT` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/study1/`, `runs/{run_id}/batch-input/study1/`, `runs/{run_id}/batch-output/study1/*-job.json` | manifest読込 -> Bedrock入力変換 -> jobメタ保存 |
| `STUDY1_BATCH_POLL` | 0 | 1 | 1 | 0 | `runs/{run_id}/batch-output/study1/*-job.json` | job状態参照、完了時メタ更新 |
| `STUDY1_NORMALIZE` | 1 | 1 | 0 | 0 | `runs/{run_id}/batch-output/study1/*.jsonl`, `runs/{run_id}/normalized/study1/*.jsonl`, `runs/{run_id}/invalid/study1/{model}/invalid.jsonl` | 出力正規化と不正行退避 |
| `STUDY2_PREPARE` | 1 | 1 | 0 | 0 | `runs/{run_id}/normalized/study1/`, `runs/{run_id}/manifests/study2_within/`, `runs/{run_id}/manifests/study2_across/`, `runs/{run_id}/manifests/experiment_a_edit/`, `runs/{run_id}/manifests/experiment_d_blind/`, `runs/{run_id}/manifests/experiment_d_wrong_label/` | 下流phase向けmanifest生成 |
| `STUDY2_WITHIN` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/study2_within/`, `runs/{run_id}/batch-input/study2_within/`, `runs/{run_id}/batch-output/study2_within/`, `runs/{run_id}/normalized/study2_within/`, `runs/{run_id}/invalid/study2_within/` | submit/poll/normalize実行 |
| `STUDY2_ACROSS` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/study2_across/`, `runs/{run_id}/batch-input/study2_across/`, `runs/{run_id}/batch-output/study2_across/`, `runs/{run_id}/normalized/study2_across/`, `runs/{run_id}/invalid/study2_across/` | submit/poll/normalize実行 |
| `EXPERIMENT_A` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/experiment_a_edit/`, `runs/{run_id}/normalized/experiment_a_edit/`, `runs/{run_id}/manifests/experiment_a_predict/`, `runs/{run_id}/batch-input/experiment_a_predict/`, `runs/{run_id}/batch-output/experiment_a_predict/`, `runs/{run_id}/normalized/experiment_a/results.jsonl`, `runs/{run_id}/invalid/experiment_a/` | edit -> predict -> 正規化 |
| `EXPERIMENT_D` | 1 | 1 | 1 | 0 | `runs/{run_id}/manifests/experiment_d_blind/`, `runs/{run_id}/manifests/experiment_d_wrong_label/`, `runs/{run_id}/manifests/experiment_d_predict/`, `runs/{run_id}/batch-input/experiment_d_predict/`, `runs/{run_id}/batch-output/experiment_d_predict/`, `runs/{run_id}/normalized/experiment_d/results.jsonl`, `runs/{run_id}/invalid/experiment_d/` | blind/wrong-label -> predict -> 正規化 |
| `REPORT` | 1 | 1 | 0 | 0 | `runs/{run_id}/normalized/*`, `runs/{run_id}/reports/study1_summary.csv`, `runs/{run_id}/reports/study2_within.csv`, `runs/{run_id}/reports/study2_across.csv`, `runs/{run_id}/reports/experiment_a.csv`, `runs/{run_id}/reports/experiment_d.csv`, `runs/{run_id}/reports/run_manifest.json`, `runs/{run_id}/reports/artifact_index.json` | 正規化済みデータ読込とレポート出力 |

### 補足
- `D`（`DeleteObject`）は未使用。
- `U` は `*-job.json` など同一キーへの再書込を指す。
- `GET /runs/{run_id}/artifacts` は成果物本文ではなくキー一覧を返す。

## エラー契約
- `400 Bad Request`: 入力不正（必須不足、制約違反、`limit` / `next_token` 不正を含む）
- `404 Not Found`: 未知 `run_id`
- `409 Conflict`: 重複起動拒否（同一 `idempotency_key` が異条件、repair の親run未終端、対象 invalid 不在、重複 repair 要求）
- `500 Internal Server Error`: durable 起動失敗や状態取得失敗

## 状態遷移
`QUEUED -> RUNNING -> SUCCEEDED|FAILED|PARTIAL`

- `PARTIAL` は主要レポート出力済みかつ `invalid/` 除外継続で完走した状態を示す。

## 受入条件
- `POST /runs` が `202` と `run_id` を返し、`config.json` 保存済みである。
- `GET /runs` で run 一覧、継続トークン、run ごとの S3 状況サマリが取得できる。
- `GET /runs/{run_id}` で [[RQ-GL-003|phase]]/state/progress/last_error が取得できる。
- `GET /runs/{run_id}/artifacts` に 5 CSV + `run_manifest.json` が含まれる。

## 変更履歴
- 2026-03-11: `POST /runs/{run_id}/repairs` と lineage/repair 応答項目を追加 [[RQ-RDR-003]]
- 2026-03-06: `GET /runs` を追加し、run 一覧 + S3 状況サマリの契約を追記 [[DD-INF-DEP-001]]
- 2026-03-02: S3 IF（API x phase x CRUD）を追記し、APIごとのS3ファイル操作境界を明記 [[RQ-FR-004]]
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]制御APIの入出力契約を定義） [[BD-SYS-ADR-001]]
