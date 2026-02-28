---
id: DD-INF-DATA-001
title: runデータ契約詳細
doc_type: データ契約
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
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

## deterministic ID
- `record_id = sha256(run_id + phase + model + target + prompt_type + temp + loop_index)` とする。
- 再試行・再実行でも同一条件なら同一 `record_id` を生成する。

## S3 格納契約
- `runs/{run_id}/config.json`
- `runs/{run_id}/manifests/{phase}/{model}/part-xxxxx.jsonl`
- `runs/{run_id}/batch-output/{phase}/{model}/...`
- `runs/{run_id}/normalized/{phase}/...jsonl`
- `runs/{run_id}/invalid/{phase}/{model}/...jsonl`
- `runs/{run_id}/reports/study1_summary.csv`
- `runs/{run_id}/reports/study2_within.csv`
- `runs/{run_id}/reports/study2_across.csv`
- `runs/{run_id}/reports/experiment_a.csv`
- `runs/{run_id}/reports/experiment_d.csv`
- `runs/{run_id}/reports/run_manifest.json`

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
- strict JSON + Pydantic 検証の成功/失敗で `normalized/` と `invalid/` が分離される。
- `run_manifest.json` から [[RQ-GL-003|phase]]別件数、retry、invalid を追跡できる。
- 同一条件再実行で `record_id` が一致する。

## 変更履歴
- 2026-02-28: 初版作成（[[RQ-GL-012|canonical schema]] と成果物契約を定義） [[BD-SYS-ADR-001]]
