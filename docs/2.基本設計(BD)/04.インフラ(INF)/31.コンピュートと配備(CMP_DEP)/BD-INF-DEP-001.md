---
id: BD-INF-DEP-001
title: コンピュートと配備設計（Bedrock Batch + Durable）
doc_type: デプロイ設計
phase: BD
version: 1.0.3
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-06'
up:
  - '[[RQ-PP-001]]'
  - '[[RQ-SC-001]]'
  - '[[RQ-PC-001]]'
related:
  - '[[BD-SYS-ADR-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-014]]'
  - '[[RQ-COST-001-01]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-INF-OVR-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-INF-IAM-001]]'
  - '[[DD-INF-MON-001]]'
  - '[[DD-APP-OVR-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - BD
  - DEP
---

## 目的
- Study1 / Study2 / 追加実験 A / D を、`ap-southeast-2` の単一リージョンでフルサーバレス運用する。
- 実験成立に必要な最小構成で運用し、コスト最小化を最優先とする。

## 設計前提（固定）
- リージョン: `ap-southeast-2`
- 実行方式: Bedrock Batch Inference（同期推論は不採用）
- 長時間制御: Lambda Durable Functions
- 利用者: [[RQ-SH-001|管理者]]のみ
- 運用形態: 常時開放しない（必要時のみ起動）
- 冗長構成: 不採用（単一環境・非冗長）

## 必須設計項目（BDで必ず決める）
- 実行基盤: API Gateway + Lambda + S3 + DynamoDB + Bedrock Batch + CloudWatch（任意で SNS）。
- 状態管理: DynamoDB は run summary projection、S3 は成果物本体、durable runtime はワークフロー進行の正本とする。
- 長時間制御: `orchestrator_durable_fn` を Lambda Durable Functions 前提で作成し、alias `live` 経由で起動する。
- モデル固定: `apac.amazon.nova-micro-v1:0`, `google.gemma-3-12b-it`, `mistral.ministral-3-8b-instruct`, `qwen.qwen3-32b-v1:0`。
- フェーズ境界: Study1 -> Study2(within/across) -> 実験A(edit/predict) -> 実験D([[RQ-GL-010|blind]]/[[RQ-GL-011|wrong-label]]) -> report。
- Bedrock Batch へ投入する [[RQ-GL-004|shard]] は 1 job あたり `100..500 records` を保証し、末尾不足は再配分、成立しない件数は submit 前 validation error とする。

## 全体構成
```text
Client (Admin only)
  -> API Gateway (HTTP API)
    -> start_run_fn
      -> orchestrator_durable_fn:live
         -> Bedrock Batch Inference
         -> S3 (config / manifests / output / normalized / reports / invalid)
         -> DynamoDB (run summary projection)
         -> CloudWatch Logs / Metrics
         -> SNS or EventBridge (optional)
    -> status_fn
      -> DynamoDB projection
      -> durable execution metadata (optional enrichment)
    -> list_runs_fn
      -> DynamoDB projection
      -> S3 status summary
    -> artifacts_fn
      -> S3 artifact keys
```

## AWS リソース
| 区分 | 論理名 | 役割 |
|---|---|---|
| S3 | `llm-temp-introspection-artifacts` | [[RQ-GL-002|run]] 単位成果物の保存 |
| Lambda | `start_run_fn` | 入力検証、`run_id` 発行、durable 起動 |
| Lambda | `orchestrator_durable_fn` | durable orchestration、Batch 投入、wait、正規化、集計 |
| Lambda Alias | `live` | durable 起動先の固定 |
| Lambda | `list_runs_fn` | run 一覧と S3 状況サマリ API |
| Lambda | `status_fn` | projection / durable 状態参照 API |
| Lambda | `artifacts_fn` | 成果物一覧 API |
| API Gateway | HTTP API | `/runs` 系エンドポイント提供 |
| DynamoDB | `run_control_table` | `RunSummary` / `idempotency` の正本 |
| IAM | Lambda実行ロール / Bedrockサービスロール | 最小権限で S3/Bedrock/durable を制御 |
| CloudWatch | Logs / Alarms | 失敗検知、実行監視 |
| SNS (任意) | 通知トピック | 完了/失敗通知 |

## S3 キー設計
- `runs/{run_id}/config.json`
- `runs/{run_id}/manifests/{phase}/{model}/part-xxxxx.jsonl`
- `runs/{run_id}/batch-output/{phase}/{model}/...`
- `runs/{run_id}/normalized/{phase}/...jsonl`
- `runs/{run_id}/reports/...`
- `runs/{run_id}/tmp/...`

## CDK 方針
- `orchestrator_durable_fn` は durable config を有効化した関数として配備する。
- `GET /runs` は low-frequency な運用APIとし、DynamoDB 全走査 + S3 集計を許容する。
- API から durable 実行を起動する場合は alias ARN を必須にする。
- execution 名は `run_id` とし、重複起動抑止を durable runtime 側へ委譲する。
- `AllowInvokeLatest` には依存せず、常に alias `live` を更新して切り替える。

## 受入基準
- 単一リージョンで 4 モデル + A/D 実験を含む [[RQ-GL-002|run]] の設計境界が明確である。
- 単一環境・非冗長・管理者単独利用の制約を満たしている。
- DD に引き渡す実行フェーズ、S3 契約、IAM 契約が揃っている。
- self-invoke や DDB lease に依存しない durable orchestration である。
- 管理者が run 一覧と S3 保存状況を API だけで確認できる。

## 変更履歴
- 2026-03-12: Bedrock Batch shard の `100..500` 保証と submit 前 validation 方針を追記 [[DD-INF-DEP-002]]
- 2026-03-06: `list_runs_fn` と `GET /runs` の運用APIを追加 [[DD-INF-API-001]]
- 2026-03-06: `orchestrator_durable_fn:live` と projection ベースの durable 構成へ更新 [[DD-INF-DEP-001]]
- 2026-02-28: DD-INF/DD-APP 正本分離に合わせ reverse trace を拡張 [[BD-SYS-ADR-001]]
- 2026-02-28: 制約（コスト最小化/単一環境/管理者単独/非冗長）を反映した基本設計へ更新 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（plan.md の前提・費用・構成をBDへ固定） [[BD-SYS-ADR-001]]
