---
id: RQ-FR-011
title: strict JSONでモデル出力を取得できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related:
  - '[[RQ-GL-012]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-011
- 種別: 機能要求
- 優先度: MUST
- 要求: Batch 出力を strict JSON として受け取り、schema 検証できる。
- 根拠: 構造化解析の失敗率を下げるため。
- 受入基準: Pydantic 検証成功レコードのみ normalized に保存される。
- 例外/エラー: 検証失敗は `invalid/` に退避する。
- 依存・関連: [[RQ-GL-012]]

## 変更履歴
- 2026-02-28: strict JSON のデータ契約追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
