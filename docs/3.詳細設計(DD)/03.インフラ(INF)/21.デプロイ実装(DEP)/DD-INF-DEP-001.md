---
id: DD-INF-DEP-001
title: デプロイ詳細（Durable Orchestration）
doc_type: デプロイ詳細
phase: DD
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
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
- durable 実行は `orchestrator_fn`（alias ARN）を起点にし、ワークフロー全体の長時間待機を Lambda Durable Functions で処理する。
- `start_run_fn` は `run_id` 発行と `config.json` 保存までを担当し、重い処理は実行しない。
- すべての推論は Bedrock Batch Inference で実行し、同期 invoke を行わない。

## 正本参照
- API入出力契約の正本は [[DD-INF-API-001]] とする。
- [[RQ-GL-012|canonical schema]] と成果物契約の正本は [[DD-INF-DATA-001]] とする。
- IAM最小権限は [[DD-INF-IAM-001]]、監視・通知は [[DD-INF-MON-001]]、CI/CD実装は [[DD-INF-PIPE-001]] を参照する。

## API 仕様（最小）
| メソッド | パス | 役割 |
|---|---|---|
| `POST` | `/runs` | [[RQ-GL-002|run]] 作成と durable 実行開始 |
| `GET` | `/runs/{run_id}` | [[RQ-GL-002|run]] 状態取得 |
| `GET` | `/runs/{run_id}/artifacts` | 成果物一覧取得 |

## `POST /runs` の処理
1. 入力検証（`loops=10`, `full_cross=true`, editor 固定など）。
2. `run_id` を生成。
3. `runs/{run_id}/config.json` を S3 保存。
4. `orchestrator_fn` の alias ARN を指定して durable 実行開始。
5. `202 Accepted` と `run_id` を返却。

## durable step 定義
1. Study1 列挙
   - 4モデル x 11温度 x 3 prompt x 5 target x 10 loops = 6,600 records を列挙する。
2. Batch submit
   - [[RQ-GL-004|shard]] 単位で `CreateModelInvocationJob` を実行する。
3. Job poll
   - `GetModelInvocationJob` を 2-5 分間隔で実行し、完了待ちを durable state へ退避する。
4. 正規化
   - Batch output を strict JSON として検証し、Pydantic で [[RQ-GL-012|canonical schema]] 化する。
5. Study2 候補生成
   - Study2: `low<=0.2`, `high>=0.8`。
   - 実験A/D: `low<=0.5`, `high>=0.8`。
6. Study2 within 実行
7. Study2 across 実行（self は within でカバーするため除外）
8. 実験A 実行（edit -> predict）
9. 実験D 実行（[[RQ-GL-010|blind]] / [[RQ-GL-011|wrong-label]]）
10. 集計・レポート出力

## [[RQ-GL-012|canonical schema]]（最小）
- `Study1Record`: `model_id`, `temperature`, `prompt_type`, `target`, `loop_index`, `generated_sentence`, `reasoning`, `judgment`
- `PredictionRecord`: `generator_model`, `predictor_model`, `phase`, `source_record_id`, `predicted_label`, `raw_text`
- `RunConfig`, `RunStatus`

## deterministic ID
- レコードIDは `sha256(run_id + phase + model + target + prompt_type + temp + loop_index)` で生成する。
- retry 実行時も同一 ID を再利用し、重複集計を防ぐ。

## 出力成果物
- `reports/study1_summary.csv`
- `reports/study2_within.csv`
- `reports/study2_across.csv`
- `reports/experiment_a.csv`
- `reports/experiment_d.csv`
- `reports/run_manifest.json`

## 障害ハンドリング
- Bedrock job failure: [[RQ-GL-004|shard]] 単位で 1 回再試行。
- JSON parse failure: `invalid/` へ退避し、後続集計から除外。
- step failure: `RunStatus` に失敗 step / reason / retry 可否を記録。

## 変更履歴
- 2026-02-28: API/データ/IAM/監視/CI_CDの正本分離を追記 [[BD-SYS-ADR-001]]
- 2026-02-28: FR/GL への要求トレーサビリティリンクを追加 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（plan.md の 0-9 step と POC 出力構成をDDへ落とし込み） [[BD-SYS-ADR-001]]
