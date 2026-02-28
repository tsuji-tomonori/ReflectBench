---
id: RQ-FR-005
title: Study1タスクを全組合せで列挙できる
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
  - '[[DD-INF-DEP-001]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-005
- 種別: 機能要求
- 優先度: MUST
- 要求: Study1 を 4モデル x 11温度 x 3prompt x 5target x 10loops で列挙できる。
- 根拠: 実験前提条件を固定するため。
- 受入基準: 6,600 records が [[RQ-GL-005|manifest]] 化される。
- 例外/エラー: 条件不足時は列挙を開始しない。
- 依存・関連: [[RQ-GL-005]]

## 変更履歴
- 2026-02-28: Study1 列挙のアプリモジュール追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
