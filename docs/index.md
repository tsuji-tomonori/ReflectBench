---
id: index
title: ホーム
doc_type: ホーム
phase: RQ
version: 1.0.3
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-01'
up: []
related:
  - '[[RQ-PP-001]]'
  - '[[RQ-SC-001]]'
  - '[[RQ-PC-001]]'
  - '[[RQ-SH-001]]'
  - '[[RQ-GL-001]]'
  - '[[RQ-UC-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-AV-001-01]]'
  - '[[RQ-RDR-001]]'
  - '[[RQ-RDR-002]]'
  - '[[RQ-DG-001]]'
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
  - '[[BD-SYS-ADR-001]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-APP-OVR-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - HM
---

## 入口
- [[RQ-PP-001]]
- [[RQ-SC-001]]
- [[RQ-PC-001]]
- [[RQ-SH-001]]
- [[RQ-GL-001]]
- [[RQ-UC-001]]
- [[RQ-FR-001]]
- [[RQ-AV-001-01]]
- [[RQ-RDR-001]]
- [[RQ-RDR-002]]
- [[RQ-DG-001]]
- [[BD-INF-DEP-001]]
- [[BD-INF-DEP-002]]
- [[BD-SYS-ADR-001]]
- [[DD-INF-DEP-001]]
- [[DD-INF-DEP-002]]
- [[OPSREL-RUN-001]]

## 推奨読書順（上から読む）
1. [[RQ-PP-001]]（目的と成果物）
2. [[RQ-SC-001]]（スコープ）
3. [[RQ-PC-001]]（プロジェクト制約）
4. [[RQ-GL-001]]（用語）
5. [[RQ-FR-001]]（機能要求）
6. [[RQ-AV-001-01]]（非機能要求）
7. [[BD-INF-DEP-001]]（単一リージョンのデプロイ基本設計）
8. [[BD-INF-DEP-002]]（CI/CD と品質ゲート）
9. [[DD-INF-DEP-001]]（Durable + Batch 実装詳細）
10. [[DD-INF-DEP-002]]（運用パラメータと再試行詳細）
11. [[DD-APP-OVR-001]]（アプリ詳細総論）
12. [[DD-APP-API-001]]（[[RQ-GL-002|run]]制御APIアプリ実装）
13. [[DD-APP-DATA-001]]（アプリデータ契約）
14. [[OPSREL-RUN-001]]（運用ランブック）

## 注記
- `docs/2.基本設計(BD)/03.アプリ(APP)` 配下は旧文脈の参考文書を含む。現行スコープの正本は RQ-SC/DD-INF/DD-APP を優先する。
- 正本分担: インフラ/全体像は `plan.md`、実験詳細は `.ai_workspace/llm-temp-introspection` を参照する。
- 実行方法と障害切り分けは [[OPSREL-RUN-001]] に集約しており、CLI 手順（run 開始/監視）とデバッグ手順（Logs/S3/DynamoDB）を参照する。

## 変更履歴
- 2026-03-01: 運用ランブック（OPSREL-RUN-001）に実行/デバッグ手順を追加した旨を注記へ反映 [[RQ-RDR-002]]
- 2026-02-28: 正本分担（plan /.ai_workspace）を注記へ追加 [[RQ-RDR-002]]
- 2026-02-28: 現行スコープに合わせて入口からBD-APP導線を外し、旧文脈は注記へ集約 [[RQ-RDR-002]]
- 2026-02-28: APP基本設計（BD-APP-API/DATA/UI/QUAL）への導線を追加 [[BD-SYS-ADR-001]]
- 2026-02-28: DD-APP文書群への導線を追加 [[RQ-RDR-002]]
- 2026-02-28: プロジェクト制約（RQ-PC-001）への導線を追加 [[RQ-RDR-002]]
- 2026-02-28: SC/SH/GL/UC/FR/NFR 文書群への導線を追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成（Bedrock Batch + Lambda Durable Functions 構成の文書導線を定義） [[RQ-RDR-001]]
