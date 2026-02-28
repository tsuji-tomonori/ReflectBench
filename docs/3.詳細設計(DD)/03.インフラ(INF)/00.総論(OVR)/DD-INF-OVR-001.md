---
id: DD-INF-OVR-001
title: インフラ詳細設計総論
doc_type: インフラ詳細
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
related:
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-INF-IAM-001]]'
  - '[[DD-INF-MON-001]]'
  - '[[DD-INF-PIPE-001]]'
  - '[[DD-APP-OVR-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - DD
  - INF
---

## 詳細仕様
- DD-INF 配下を「総論 + 実行詳細 + 契約詳細 + 運用詳細」の4層で管理し、設定値の正本境界を固定する。
- デプロイ実装は `DD-INF-DEP-*`、API契約は `DD-INF-API-001`、データ契約は `DD-INF-DATA-001`、IAMは `DD-INF-IAM-001`、監視は `DD-INF-MON-001`、CI/CDは `DD-INF-PIPE-001` を正本とする。

## 正本境界
| 領域 | 正本文書 | 本書での扱い |
|---|---|---|
| durable step / [[RQ-GL-003|phase]] 実行順 | [[DD-INF-DEP-001]] | 実行フローの参照境界のみ定義 |
| 実行パラメータ / retry | [[DD-INF-DEP-002]] | 運用初期値と復旧方針の参照 |
| `/runs` API 入出力契約 | [[DD-INF-API-001]] | エンドポイント責務の参照 |
| [[RQ-GL-012|canonical schema]] / 成果物契約 | [[DD-INF-DATA-001]] | データ整合境界の参照 |
| 最小権限IAM | [[DD-INF-IAM-001]] | 権限統制の参照 |
| メトリクス / アラーム | [[DD-INF-MON-001]] | 可観測性境界の参照 |
| docs + deploy ワークフロー | [[DD-INF-PIPE-001]] | 配備統制の参照 |

## 章構成
1. 総論（本書）
2. デプロイ実装（durable orchestration）
3. API契約（[[RQ-GL-002|run]]制御API）
4. データ契約（strict JSON + Pydantic）
5. 監視設定（CloudWatch + Alarm）
6. セキュリティ詳細（IAM最小権限）
7. CI/CD詳細（docs:deploy チェーン）

## 変更履歴
- 2026-02-28: 初版作成（DD-INF の正本境界と章構成を定義） [[BD-SYS-ADR-001]]
