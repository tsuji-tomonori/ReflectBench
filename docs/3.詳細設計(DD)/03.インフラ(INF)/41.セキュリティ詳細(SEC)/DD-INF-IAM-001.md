---
id: DD-INF-IAM-001
title: IAM最小権限設計
doc_type: セキュリティ詳細
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
  - '[[RQ-SEC-001-01]]'
tags:
  - llm-temp-introspection
  - DD
  - SEC
---

## 詳細仕様
- Lambda実行ロールと Bedrock Batch サービスロールを分離し、最小権限で運用する。
- 許可対象は S3、DynamoDB、Bedrock Batch API、CloudWatch、durable execution API に限定する。
- self-invoke を前提にした `lambda:InvokeFunction` は orchestrator 自身へ付与しない。

## ロール定義
| ロール | 主体 | 主な責務 |
|---|---|---|
| `start_run_fn_role` | Lambda | 入力検証、`config.json` 保存、durable起動 |
| `orchestrator_durable_fn_role` | Lambda | Batch投入、durable wait、正規化、集計 |
| `list_runs_fn_role` | Lambda | run 一覧と S3 状況サマリ参照 |
| `status_fn_role` | Lambda | status / durable execution 参照 |
| `artifacts_fn_role` | Lambda | S3成果物参照 |
| `bedrock_batch_service_role` | Bedrock | job実行時のS3入出力アクセス |

## 許可アクション（必須）
### `start_run_fn_role`
- `s3:PutObject` on `runs/*/config.json`
- `dynamodb:PutItem`, `dynamodb:UpdateItem`, `dynamodb:ConditionCheckItem`, `dynamodb:GetItem` on `run_control_table`
- `lambda:InvokeFunction` on `orchestrator_durable_fn:live`
- `cloudwatch:PutMetricData`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### `orchestrator_durable_fn_role`
- `bedrock:CreateModelInvocationJob`, `bedrock:GetModelInvocationJob`
- Bedrock resource ARN は `foundation-model/*`, `inference-profile/*`, `application-inference-profile/*`, `model-invocation-job/*` を許可する。
- `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on `runs/{run_id}/*`
- `dynamodb:GetItem`, `dynamodb:UpdateItem` on `run_control_table`
- `cloudwatch:PutMetricData`
- `iam:PassRole` on `bedrock_batch_service_role`
- durable execution 権限は `AWSLambdaBasicDurableExecutionRolePolicy` または同等の `lambda:ManageDurableState`, `lambda:GetDurableExecution`, `lambda:ListDurableExecutions` を付与する。

### `status_fn_role`
- `dynamodb:GetItem` on `run_control_table`
- `lambda:GetDurableExecution`, `lambda:ListDurableExecutions` on `orchestrator_durable_fn` versions / alias
- `logs:FilterLogEvents`（必要最小範囲）

### `list_runs_fn_role`
- `dynamodb:Scan` on `run_control_table`
- `s3:GetObject`, `s3:ListBucket` on `runs/{run_id}/*`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### `artifacts_fn_role`
- `s3:GetObject`, `s3:ListBucket` on `runs/{run_id}/*`

### `bedrock_batch_service_role`
- trust policy: `bedrock.amazonaws.com`
- `s3:GetObject` on input [[RQ-GL-005|manifest]] prefix
- `s3:PutObject` on batch output prefix
- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` on `foundation-model/*`, `inference-profile/*`, `application-inference-profile/*`

## 制約
- `Resource: *` は原則禁止し、prefix または ARN を明示する。
- 一時権限付与時は期限と理由を運用ログへ記録する。
- role の追加権限はレビュー時に `変更理由 + 影響範囲` を必須記載する。
- durable execution は alias 起動を前提とし、`$LATEST` への直接 invoke を運用経路に含めない。

## 監査観点
- 四半期ごとに未使用権限を棚卸しし、削除計画を記録する。
- `AccessDenied` の発生時は暫定拡張せず、要求アクションと対象リソースを特定してから追加する。
- durable execution 権限の付与範囲が start/status/orchestrator の責務境界と一致していることを確認する。
- `list_runs_fn_role` に write 系権限が混入していないことを確認する。

## 受入条件
- Lambda実行ロールに不要サービス権限がない。
- BedrockサービスロールのS3アクセスが [[RQ-GL-002|run]] prefix へ限定されている。
- self-invoke 用の不要権限が残っていない。
- `list_runs_fn_role` が read-only 権限のみで成立している。
- IAM変更が `DD-INF-DEP-*` と矛盾しない。

## 変更履歴
- 2026-03-06: `list_runs_fn_role` と read-only 権限を追加 [[DD-INF-API-001]]
- 2026-03-06: durable execution 権限を追記し、self-invoke 前提の権限を削除 [[DD-INF-DEP-001]]
- 2026-03-01: Bedrock profile/モデル解決の失敗対策として許可リソースと batch service role の invoke 権限を拡張 [[DD-INF-DEP-001]]
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]実行基盤の最小権限IAMを定義） [[BD-SYS-ADR-001]]
