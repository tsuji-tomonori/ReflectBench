---
id: BD-INF-DEP-002
title: CI/CD基本設計（docs + deploy）
doc_type: デプロイ設計
phase: BD
version: 1.0.2
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-DG-001]]'
related:
  - '[[BD-SYS-ADR-001]]'
  - '[[BD-INF-DEP-001]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-PIPE-001]]'
  - '[[DD-INF-MON-001]]'
  - '[[DD-INF-IAM-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - BD
  - DEP
---

## 目的
- ドキュメント検証とデプロイ実行を同一チェーンで管理し、再現可能な公開運用を維持する。

## 必須設計項目（BDで必ず決める）
- 入口: `workflow_dispatch` と `push(main)`。
- 承認境界: `environment: prod`。
- 実行順: `docs:guard -> infra:deploy -> docs:verify`。
- 直列化: `concurrency` で本番配備を多重実行しない。

## 実行チェーン
- 標準コマンドは `task docs:deploy`。
- CI 実行は `task docs:deploy:ci`。
- `docs:guard` は用語リンク補正 + docs 検証のゲートとして必須。

## Workflow 方針
- `docs-link-check`: docs 変更時の静的検証を実行。
- `docs-deploy`: 段階導入とし、通常は `docs:guard` のみ実行、`workflow_dispatch` の `execute_deploy=true` 時のみ OIDC 認証で AWS ロールを Assume し、`task docs:deploy:ci` を実行。
- `docs-pdf`（任意）: 単一 PDF 生成と artifact 配布を行う。

## 認証・権限方針
- GitHub Actions は OIDC のみを使用し、長期アクセスキーを使用しない。
- `permissions` は最小構成（`id-token: write`, `contents: read`）に固定する。
- Assume 後に `aws sts get-caller-identity` で誤アカウント配備を検知する。

## 品質ゲート
- docs 更新は `docs:guard` を通過しない限り配備しない。
- infra 更新は `lint` / `test` / `cdk synth` / `cdk diff` / `cdk-nag` を通過条件とする。
- 配備後に `/runs` API ヘルスと status API 参照を確認する。

## 失敗時観点
- docs 失敗: frontmatter 欠落、リンク切れ、用語リンク未整備を確認する。
- deploy 失敗: OIDC role、`AWS_REGION`、CDK context を確認する。
- 反映遅延: CloudWatch ログと API 実行履歴からどの step で停止したかを特定する。

## 受入基準
- CI/CD の入口、承認、実行順、失敗切り分けが競合なく定義されている。
- DD へ引き渡す実行条件と運用確認項目が不足なく整理されている。

## 変更履歴
- 2026-02-28: docs-deploy を手動実行条件付きの段階導入方針へ更新 [[BD-SYS-ADR-001]]
- 2026-02-28: CI/CD詳細と監視/権限の reverse trace を追加 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（diopside の `docs-deploy` 運用パターンを適用） [[BD-SYS-ADR-001]]
