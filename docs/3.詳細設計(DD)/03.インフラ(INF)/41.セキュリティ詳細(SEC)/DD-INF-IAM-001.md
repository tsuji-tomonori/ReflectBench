---
id: DD-INF-IAM-001
title: IAM最小権限設計
doc_type: セキュリティ詳細
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
  - '[[RQ-SEC-001-01]]'
tags:
  - llm-temp-introspection
  - DD
  - SEC
---

## 詳細仕様
- Lambda実行ロールと Bedrock Batch サービスロールを分離し、最小権限で運用する。
- 許可対象は S3（[[RQ-GL-002|run]] prefix 限定）/ Bedrock Batch API / CloudWatch（logs, metrics）に限定する。

## ロール定義
| ロール | 主体 | 主な責務 |
|---|---|---|
| `start_run_fn_role` | Lambda | 入力検証、`config.json` 保存、durable起動 |
| `orchestrator_fn_role` | Lambda | Batch投入、poll、正規化、集計 |
| `status_fn_role` | Lambda | status/artifacts 参照 |
| `bedrock_batch_service_role` | Bedrock | job実行時のS3入出力アクセス |

## 許可アクション（必須）
### `start_run_fn_role`
- `s3:PutObject` on `runs/*/config.json`
- `lambda:InvokeFunction` on `orchestrator_fn` alias ARN
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### `orchestrator_fn_role`
- `bedrock:CreateModelInvocationJob`, `bedrock:GetModelInvocationJob`
- `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on `runs/{run_id}/*`
- `cloudwatch:PutMetricData`（namespace 固定）
- `logs:*`（作成/書き込み系のみ）

### `status_fn_role`
- `s3:GetObject`, `s3:ListBucket` on `runs/{run_id}/*`
- `logs:FilterLogEvents`（必要最小範囲）

### `bedrock_batch_service_role`
- trust policy: `bedrock.amazonaws.com`
- `s3:GetObject` on input [[RQ-GL-005|manifest]] prefix
- `s3:PutObject` on batch output prefix

## 制約
- `Resource: *` は禁止し、prefix または ARN を明示する。
- 一時権限付与時は期限と理由を運用ログへ記録する。
- role の追加権限はレビュー時に `変更理由 + 影響範囲` を必須記載する。

## 監査観点
- 四半期ごとに未使用権限を棚卸しし、削除計画を記録する。
- `AccessDenied` の発生時は暫定拡張せず、要求アクションと対象リソースを特定してから追加する。

## 受入条件
- Lambda実行ロールに不要サービス権限がない。
- BedrockサービスロールのS3アクセスが [[RQ-GL-002|run]] prefix へ限定されている。
- IAM変更が `DD-INF-DEP-*` と矛盾しない。

## 変更履歴
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]実行基盤の最小権限IAMを定義） [[BD-SYS-ADR-001]]
