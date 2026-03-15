---
id: DD-APP-DATA-001
title: アプリデータモデル詳細
doc_type: データ契約
phase: DD
version: 1.3.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-14'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[RQ-FR-011]]'
  - '[[RQ-FR-013]]'
  - '[[RQ-FR-014]]'
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-016]]'
  - '[[RQ-FR-017]]'
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-019]]'
  - '[[RQ-FR-020]]'
tags:
  - llm-temp-introspection
  - DD
  - APP
  - DATA
---

## 詳細仕様
- [[RQ-GL-012|canonical schema]] は [[DD-INF-DATA-001]] を正本とし、本書はアプリ側クラス定義と変換責務を定義する。
- strict JSON の decode 後に Pydantic モデルへ変換し、型不一致は例外化して `invalid/` へ送る。
- 状態管理（`RunStatus`/`idempotency`）と canonical result は DynamoDB、raw artifact / report は S3 を正本とする。

## アプリモデル
| モデル | 用途 | 主なフィールド |
|---|---|---|
| `RunCreateRequest` | API入力 | loops, full_cross, [[RQ-GL-004|shard]]_size, poll_interval_sec |
| `RunCancelRequest` | cancel API入力 | reason |
| `RepairRunCreateRequest` | repair API入力 | phase, scope, mode, models, record_ids, rebuild_downstream |
| `RunResultsQuery` | results API入力 | run_id, phase, experiment_id, limit, next_token |
| `RunCreateResponse` | API出力 | [[RQ-GL-002|run]]_id, accepted_at, initial_[[RQ-GL-003|phase]], state |
| `RunStatusView` | 状態応答 | [[RQ-GL-003|phase]], state, progress, retry_count, last_error, lineage, repair, cancel |
| `ExperimentResultView` | results API出力 | experiment_id, phase, prompt, normalized_result, source, metadata |
| `RunResultsResponse` | results API出力 | run_id, results[], returned_count, next_token |
| `RepairSeedRow` | repair seed | record_id, model_id, manifest_row, invalid_output, source_invalid_key |
| `ManifestLine` | Batch入力行 | record_id, prompt_payload, output_key |
| `InvalidRecord` | 検証失敗保存 | record_id, [[RQ-GL-003|phase]], reason, raw_text |
| `BackfillCandidate` | direct rerun入力 | experiment_id, prompt_payload, model routing, source metadata |

## 変換ルール
- `RunStatus` -> `RunStatusView` 変換で `datetime` は ISO8601(UTC) へ統一する。
- `PredictionRecord` の `predicted_label` は語彙正規化後に保存する。
- `record_id` は生成関数を単一化し、呼び出し側で直接生成しない。
- `experiment_id` は外部 view では `record_id` の別名として扱い、serializer が両者を整形する。
- `condition_type` は `self_reflection`, `within_model`, `across_model`, `blind`, `wrong_label`, `info_plus`, `info_minus` を受理する。
- repair run の `lineage.parent_run_id` と `repair.source_invalid_keys` は DynamoDB 正本から serializer で応答へ整形する。
- cancel request の `cancel_requested_at`, `cancel_reason`, `cancel_requested_phase`, `cancel_requested_step` は `cancel` オブジェクトへ整形する。
- `prompt_payload` は DDB item の `prompt` object へ、`acquired_via/source_artifact_key/source_run_id` は `source` object へ整形する。

## I/O責務
- 入力: batch output JSON、[[RQ-GL-002|run]]設定JSON、status中間データ。
- 出力: canonical result DDB item、normalized JSONL mirror、invalid JSONL、report 用 CSV レコード。

## 実験詳細プロファイルの追加成果物
- `output/study2/summary.csv`
- `output/analysis/experiment_a_p_high_delta.csv`
- `output/analysis/experiment_d_accuracy_by_label_condition.csv`
- `output/analysis/experiment_d_wrong_label_shift.csv`

## 受入条件
- Pydantic モデルで schema 不整合を検出できる。
- 同一条件では常に同一 `record_id` を生成する。

## 変更履歴
- 2026-03-14: results API / canonical result / backfill 用アプリモデルを追加 [[RQ-RDR-005]]
- 2026-03-13: `RunCancelRequest` と `RunStatusView.cancel` の変換責務を追加 [[RQ-FR-017]]
- 2026-02-28: condition_type 列挙値と分析成果物CSVを追記 [[RQ-RDR-002]]
- 2026-03-11: repair API 入力、status/list/artifacts 向け lineage/repair view、repair seed 行を追記 [[RQ-RDR-003]]
- 2026-02-28: 初版作成（アプリ側データモデルと変換責務を定義） [[BD-SYS-ADR-001]]
