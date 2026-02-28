---
id: RQ-FR-004
title: 実験成果物APIで出力一覧を取得できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-004]]'
related:
  - '[[RQ-GL-005]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-004
- 種別: 機能要求
- 優先度: MUST
- 要求: `GET /runs/{run_id}/artifacts` で reports/normalized/invalid 一覧を取得できる。
- 根拠: 結果参照の入口を統一するため。
- 受入基準: 主要CSVと [[RQ-GL-002|run]]_[[RQ-GL-005|manifest]] が一覧に含まれる。
- 例外/エラー: 出力未生成時は空配列と状態を返す。
- 依存・関連: [[RQ-UC-004]]

## 変更履歴
- 2026-02-28: artifacts API の詳細契約追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
