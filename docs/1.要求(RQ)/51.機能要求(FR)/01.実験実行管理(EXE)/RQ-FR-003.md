---
id: RQ-FR-003
title: run状態APIでphase進捗を取得できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-002]]'
related:
  - '[[DD-INF-DEP-002]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-003
- 種別: 機能要求
- 優先度: MUST
- 要求: `GET /runs/{run_id}` で [[RQ-GL-003|phase]]/state/progress/last_error を取得できる。
- 根拠: 長時間実行の監視に必要なため。
- 受入基準: 実行中・完了・失敗の状態が区別できる。
- 例外/エラー: 未知 `run_id` は Not Found を返す。
- 依存・関連: [[RQ-UC-002]]

## 変更履歴
- 2026-02-28: state API の詳細契約追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
