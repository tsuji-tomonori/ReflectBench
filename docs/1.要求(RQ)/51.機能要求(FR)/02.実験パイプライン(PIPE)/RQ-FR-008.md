---
id: RQ-FR-008
title: Study2 withinとacrossを分離実行できる
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
  - '[[RQ-GL-008]]'
  - '[[RQ-GL-009]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-008
- 種別: 機能要求
- 優先度: MUST
- 要求: Study2 within と across を別 [[RQ-GL-005|manifest]] で実行できる。
- 根拠: 比較指標を条件別に分離するため。
- 受入基準: within/across の結果が別CSVで出力される。
- 例外/エラー: predictor 未指定時は実行を拒否する。
- 依存・関連: [[RQ-GL-008]], [[RQ-GL-009]]

## 変更履歴
- 2026-02-28: Study2 分離実行の DD-INF/DD-APP 追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
