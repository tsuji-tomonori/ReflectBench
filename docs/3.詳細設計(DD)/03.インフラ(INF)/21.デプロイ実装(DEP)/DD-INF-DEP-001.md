---
id: DD-INF-DEP-001
title: デプロイ詳細（Durable Orchestration）
doc_type: デプロイ詳細
phase: DD
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-06'
up:
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
  - '[[RQ-FR-005]]'
  - '[[RQ-FR-010]]'
related:
  - '[[RQ-PP-001]]'
  - '[[BD-SYS-ADR-001]]'
  - '[[RQ-GL-012]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-INF-OVR-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-INF-IAM-001]]'
  - '[[DD-INF-MON-001]]'
  - '[[DD-INF-PIPE-001]]'
  - '[[DD-APP-OVR-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - DD
  - DEP
---

## 詳細仕様
- durable 実行は `orchestrator_durable_fn:live` の qualified ARN を起点にし、ワークフロー全体の長時間待機を Lambda Durable Functions で処理する。
- `start_run_fn` は受付専用とし、入力検証、`config.json` 保存、DynamoDB projection 作成、durable 実行開始のみを担当する。
- `list_runs_fn` は運用向け一覧APIとして DynamoDB の run summary と S3 の保存状況を集約して返す。
- Bedrock Batch の完了待機は self-invoke ではなく durable execution の `wait_for_condition` または durable `wait` で継続する。
- DynamoDB は projection の正本とし、`phase`, `step`, `progress`, `execution_name`, `durable_execution_arn`, `artifact_index_key`, `last_error` を保持する。
- S3 はデータプレーンの正本とし、`manifest` / `batch-output` / `normalized` / `invalid` / `reports` を保存する。

## 正本参照
- API入出力契約の正本は [[DD-INF-API-001]] とする。
- [[RQ-GL-012|canonical schema]] と成果物契約の正本は [[DD-INF-DATA-001]] とする。
- IAM最小権限は [[DD-INF-IAM-001]]、監視・通知は [[DD-INF-MON-001]]、CI/CD実装は [[DD-INF-PIPE-001]] を参照する。
- 実験アルゴリズム詳細（self/within/across, A/D 条件、分析成果物）は [[DD-APP-OVR-001]] / [[DD-APP-MOD-001]] を正本とする。

## API 仕様（最小）
| メソッド | パス | 役割 |
|---|---|---|
| `POST` | `/runs` | [[RQ-GL-002|run]] 作成と durable 実行開始 |
| `GET` | `/runs` | run 一覧と S3 状況サマリ取得 |
| `GET` | `/runs/{run_id}` | [[RQ-GL-002|run]] 状態取得 |
| `GET` | `/runs/{run_id}/artifacts` | 成果物一覧取得 |

## `POST /runs` の処理
1. 入力検証（`loops=10`, `full_cross=true`, editor 固定など）。
2. `run_id` を生成し、`execution_name=run_id` を確定する。
3. `runs/{run_id}/config.json` を S3 保存する。
4. DynamoDB に `RunSummary(state=QUEUED, phase=STUDY1, step=STUDY1_ENUMERATE)` と `idempotency_key` を条件付き保存する。
5. `orchestrator_durable_fn:live` を `DurableExecutionName=run_id` で起動し、返却された `DurableExecutionArn` を保存する。
6. `DurableExecutionAlreadyStartedException` は重複起動として正規化し、既存 run を `202 Accepted` で返す。

## `GET /runs` の処理
1. DynamoDB から idempotency 行を除いた run summary を走査する。
2. `created_at` 降順で整列し、`limit` と `next_token` でページングする。
3. 各 run について `config.json`, `reports/`, `normalized/`, `invalid/`, `batch-output/` の S3 状況を集約する。
4. `artifact_index_key` がある場合は `artifact_index.json` を優先し、未完了 run は prefix 集計で補う。
5. `runs[]` と `next_token` を返す。

## durable step 定義
| child context | step | 役割 |
|---|---|---|
| `study1` | `STUDY1_ENUMERATE` | Study1 manifest 生成 |
| `study1` | `STUDY1_SUBMIT` | Study1 Batch submit |
| `study1` | `STUDY1_WAIT` | Study1 Batch 完了待機 |
| `study1` | `STUDY1_NORMALIZE` | Study1 正規化 |
| `study2` | `STUDY2_PREPARE` | Study2 / 実験A / 実験D の入力準備 |
| `study2` | `STUDY2_WITHIN_SUBMIT` | within submit |
| `study2` | `STUDY2_WITHIN_WAIT` | within wait |
| `study2` | `STUDY2_WITHIN_NORMALIZE` | within normalize |
| `study2` | `STUDY2_ACROSS_SUBMIT` | across submit |
| `study2` | `STUDY2_ACROSS_WAIT` | across wait |
| `study2` | `STUDY2_ACROSS_NORMALIZE` | across normalize |
| `experiment_a` | `EXPERIMENT_A_SUBMIT` | edit 生成と predict submit |
| `experiment_a` | `EXPERIMENT_A_WAIT` | predict wait |
| `experiment_a` | `EXPERIMENT_A_NORMALIZE` | 実験A normalize |
| `experiment_d` | `EXPERIMENT_D_SUBMIT` | blind / wrong-label 入力生成と submit |
| `experiment_d` | `EXPERIMENT_D_WAIT` | predict wait |
| `experiment_d` | `EXPERIMENT_D_NORMALIZE` | 実験D normalize |
| `report` | `REPORT_GENERATE` | CSV / run manifest / artifact index 生成 |

## durable wait の原則
- Batch pending 時は同一 durable execution が待機状態へ checkpoint される。
- 次回再開は durable runtime が同一 execution を replay し、次の poll または次 step を実行する。
- Lambda の自己再起動、cursor 管理、lease 管理は採用しない。
- 個々の Lambda invocation は 15 分以内に収め、長い処理は step 分割で扱う。

## phase 遷移図
```mermaid
flowchart TD
  A[POST /runs accepted] --> B[Durable execution start]
  B --> C[study1 child context]
  C --> D[study2 child context]
  D --> E[experiment_a child context]
  E --> F[experiment_d child context]
  F --> G[report step]
  G --> H[finalize]
  C --> C1[submit]
  C1 --> C2[wait_for_condition]
  C2 --> C3[normalize]
  D --> D1[within submit/wait/normalize]
  D1 --> D2[across submit/wait/normalize]
```

## state 遷移図
```mermaid
stateDiagram-v2
  [*] --> QUEUED
  QUEUED --> RUNNING: durable execution starts
  RUNNING --> SUCCEEDED: all steps done and invalid=0
  RUNNING --> PARTIAL: all steps done and invalid>0
  RUNNING --> FAILED: pipeline/internal error
  RUNNING --> TIMED_OUT: durable execution timeout
```

## projection 項目
- `run_id`
- `request_hash`
- `config_s3_key`
- `execution_name`
- `durable_execution_arn`
- `state`
- `phase`
- `step`
- `progress`
- `started_at`
- `finished_at`
- `last_error`
- `artifact_index_key`

## [[RQ-GL-012|canonical schema]]（最小）
- `Study1Record`: `model_id`, `temperature`, `prompt_type`, `target`, `loop_index`, `generated_sentence`, `reasoning`, `judgment`
- `PredictionRecord`: `generator_model`, `predictor_model`, `phase`, `source_record_id`, `predicted_label`, `raw_text`
- `RunConfig`, `RunSummary`

## deterministic ID
- レコードIDは `sha256(run_id + phase + model + target + prompt_type + temp + loop_index)` で生成する。
- retry 実行時も同一 ID を再利用し、重複集計を防ぐ。
- durable step 名は静的に保ち、UUID や現在時刻は step 内に閉じ込める。

## 出力成果物
- `reports/study1_summary.csv`
- `reports/study2_within.csv`
- `reports/study2_across.csv`
- `reports/experiment_a.csv`
- `reports/experiment_d.csv`
- `reports/run_manifest.json`
- `reports/artifact_index.json`

## 状態参照と成果物DL
- `GET /runs/{run_id}` は DynamoDB projection を返し、必要時のみ durable execution 情報で補強する。
- `GET /runs` は run summary に S3 状況サマリを付与して返す。
- `GET /runs/{run_id}/artifacts` は S3 キー一覧を返す。
- 実データのダウンロード元は S3 とし、DynamoDB は成果物ポインタの保持に限定する。

## 障害ハンドリング
- Bedrock job failure: [[RQ-GL-004|shard]] 単位で 1 回再試行。
- JSON parse failure: `invalid/` へ退避し、後続集計から除外する。
- duplicate start: `DurableExecutionAlreadyStartedException` を受けた場合は既存 run を返す。
- step failure: projection に失敗 step / reason / retry 可否を記録する。
- 一覧APIは管理者運用向けとし、full scan を許容する代わりに `limit<=100` を必須制約とする。

## 変更履歴
- 2026-03-06: `GET /runs` と `list_runs_fn` を追加し、S3 状況サマリ取得フローを追記 [[DD-INF-API-001]]
- 2026-03-06: self-invoke / lease / cursor 前提を削除し、durable execution + projection 構成へ更新 [[BD-INF-DEP-001]]
- 2026-03-02: Batch submit 前に `manifests -> batch-input` 変換を追加し、`messages` 必須契約と `recordId` 再結合正規化を明記 [[RQ-FR-006]]
- 2026-02-28: 実験詳細正本を DD-APP 側へ明示（infra/experiment 分担） [[RQ-RDR-002]]
- 2026-02-28: API/データ/IAM/監視/CI_CDの正本分離を追記 [[BD-SYS-ADR-001]]
- 2026-02-28: FR/GL への要求トレーサビリティリンクを追加 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（plan.md の 0-9 step と POC 出力構成をDDへ落とし込み） [[BD-SYS-ADR-001]]
