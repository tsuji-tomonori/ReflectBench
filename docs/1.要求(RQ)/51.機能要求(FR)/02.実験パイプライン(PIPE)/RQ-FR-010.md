---
id: RQ-FR-010
title: 追加実験Dをblindとwrong-labelで実行できる
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
  - '[[RQ-GL-010]]'
  - '[[RQ-GL-011]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-010
- 種別: 機能要求
- 優先度: MUST
- 要求: 実験Dを [[RQ-GL-010|blind]] と [[RQ-GL-011|wrong-label]] の2条件で実行できる。
- 根拠: ラベル依存の影響を評価するため。
- 受入基準: 条件別の出力が分離保存される。
- 例外/エラー: swap 対象外ラベルは処理対象から除外する。
- 依存・関連: [[RQ-GL-010]], [[RQ-GL-011]]

## 変更履歴
- 2026-02-28: 実験Dの DD-INF/DD-APP 追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
