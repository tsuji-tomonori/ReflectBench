---
id: BD-INF-DEP-001
title: コンピュートと配備設計（Bedrock Batch + Durable）
doc_type: デプロイ設計
phase: BD
version: 1.0.2
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
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
- 実行基盤: API Gateway + Lambda + S3 + Bedrock Batch + CloudWatch（任意で SNS）。
- 状態管理: `RunStatus` と `idempotency` は DynamoDB を正本とし、成果物本体は S3 を正本とする。
- 長時間制御: `orchestrator_fn` を Lambda Durable Functions 前提で作成する。
- モデル固定: `apac.amazon.nova-micro-v1:0`, `google.gemma-3-12b-it`, `mistral.ministral-3-8b-instruct`, `qwen.qwen3-32b-v1:0`。
- フェーズ境界: Study1 -> Study2(within/across) -> 実験A(edit/predict) -> 実験D([[RQ-GL-010|blind]]/[[RQ-GL-011|wrong-label]]) -> report。

## 全体構成
```text
Client (Admin only)
  -> API Gateway (HTTP API)
    -> StartRun Lambda
      -> Durable Orchestrator Lambda (alias ARN)
         -> Bedrock Batch Inference
         -> S3 (config / manifests / output / normalized / reports / invalid)
         -> CloudWatch Logs / Metrics
         -> SNS (optional)
    -> Status Lambda
      -> S3 / CloudWatch 参照
```

## 採用モデルとID
- Nova Micro: `apac.amazon.nova-micro-v1:0`
- Gemma 3 12B IT: `google.gemma-3-12b-it`
- Ministral 3 8B: `mistral.ministral-3-8b-instruct`
- Qwen3 32B: `qwen.qwen3-32b-v1:0`

## AWS リソース
| 区分 | 論理名 | 役割 |
|---|---|---|
| S3 | `llm-temp-introspection-artifacts` | [[RQ-GL-002|run]] 単位成果物の保存 |
| Lambda | `start_run_fn` | 入力検証、`run_id` 発行、durable 起動 |
| Lambda | `orchestrator_fn` | フェーズ列挙、Batch 投入、待機、正規化、集計 |
| Lambda | `status_fn` | 実行状態/成果物の参照 API |
| API Gateway | HTTP API | `/runs` 系エンドポイント提供 |
| DynamoDB | `run_control_table` | `RunStatus`/`idempotency` の正本 |
| IAM | Lambda実行ロール / Bedrockサービスロール | 最小権限で S3/Bedrock を制御 |
| CloudWatch | Logs / Alarms | 失敗検知、実行監視 |
| SNS (任意) | 通知トピック | 完了/失敗通知 |

## S3 キー設計
- `runs/{run_id}/config.json`
- `runs/{run_id}/manifests/{phase}/{model}/part-xxxxx.jsonl`
- `runs/{run_id}/batch-output/{phase}/{model}/...`
- `runs/{run_id}/normalized/{phase}/...jsonl`
- `runs/{run_id}/reports/...`

## 費用前提（1 [[RQ-GL-002|run]] 概算）
- Bedrock モデル費は約 `$2.66 / run`（Batch 前提）。
- オンデマンド相当は約 `$5.31 / run`。
- インフラ費（API Gateway/Lambda/S3/CloudWatch）は本ワークロードではモデル費より小さい前提とする。

## コスト方針
- 目標: 1 [[RQ-GL-002|run]] の推定モデル費を 3.50 USD 以下に維持する。
- 優先順位:
  1. モデル費削減（不要実行の抑制）
  2. 実験成立性（A/D 含む）
  3. 実行時間最適化

## 可用性方針（制約準拠）
- 常時稼働SLAは採用しない。
- 必要時起動後に [[RQ-GL-002|run]] 開始・状態確認ができることを運用基準とする。
- 障害時は冗長切替ではなく、[[RQ-GL-004|shard]]再試行と再実行で復旧する。

## CDK 方針
- `orchestrator_fn` は作成時に durable を有効化する（後付け変更を避ける）。
- API から durable 実行を起動する場合は alias ARN を必須にする。
- `cdk synth` は副作用ゼロを維持し、環境差分は props で注入する。

## 受入基準
- 単一リージョンで 4 モデル + A/D 実験を含む [[RQ-GL-002|run]] の設計境界が明確である。
- 単一環境・非冗長・管理者単独利用の制約を満たしている。
- DD に引き渡す実行フェーズ、S3 契約、IAM 契約が揃っている。

## 変更履歴
- 2026-02-28: DD-INF/DD-APP 正本分離に合わせ reverse trace を拡張 [[BD-SYS-ADR-001]]
- 2026-02-28: 制約（コスト最小化/単一環境/管理者単独/非冗長）を反映した基本設計へ更新 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（plan.md の前提・費用・構成をBDへ固定） [[BD-SYS-ADR-001]]
