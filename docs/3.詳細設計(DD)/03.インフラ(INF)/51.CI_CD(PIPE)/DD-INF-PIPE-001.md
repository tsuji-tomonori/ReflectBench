---
id: DD-INF-PIPE-001
title: CI/CD実装詳細（docs + deploy）
doc_type: CI/CD詳細
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-002]]'
related:
  - '[[DD-INF-DEP-001]]'
  - '[[RQ-DG-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - DD
  - PIPE
---

## 詳細仕様
- 実行入口は `workflow_dispatch` と `push(main)` の2系統を採用する。
- 配備チェーンは `docs:guard -> infra:deploy -> docs:verify` を固定し、品質ゲート未通過時は配備しない。

## workflow 実装
| 項目 | 設定 |
|---|---|
| Workflow名 | `docs-deploy` |
| Trigger | `workflow_dispatch`, `push` on `main` |
| Path filter | `docs/**`, `Taskfile.yaml`, `.github/workflows/docs-deploy.yml` |
| Environment | `prod` |
| Concurrency | `docs-deploy-prod`（直列化） |
| Permissions | `id-token: write`, `contents: read` |

## ジョブ手順
1. `actions/checkout`
2. `go-task/setup-task`
3. Python / Node セットアップ
4. OIDC で AWS ロール Assume
5. `aws sts get-caller-identity` で配備先アカウント確認
6. `task docs:deploy:ci` 実行

## task 実装契約
- `docs:deploy:ci` は `docs:guard -> infra:deploy -> docs:verify` を順守する。
- `docs:guard` は `docs:autolink` と `docs:check` を必須で実行する。
- `docs:verify` は `/runs` API 疎通と成果物参照手順を含む。

## 失敗時切り分け
- `docs:guard` 失敗: frontmatter不足、リンク不整合、用語リンク未補正を確認。
- Assume失敗: `AWS_ROLE_ARN`、`AWS_REGION`、OIDC trust policy を確認。
- deploy失敗: CDK context と IAM 権限、リージョン固定値の不整合を確認。
- verify失敗: API Gateway/Lambdaログと S3 成果物キーを確認。

## セキュリティ方針
- 長期アクセスキーは使用しない。
- Assume ロールは本配備に必要な最小権限へ限定する。
- workflow改変を伴う差分はコードレビューを必須とする。

## 受入条件
- 本番配備が `prod` 保護境界で直列実行される。
- `docs:guard` 不通過時に配備が停止する。
- 配備後に `docs:verify` が実行され、失敗時は原因切り分けが可能である。

## 変更履歴
- 2026-02-28: 初版作成（docs + deploy チェーンのCI/CD実装詳細を定義） [[BD-SYS-ADR-001]]
