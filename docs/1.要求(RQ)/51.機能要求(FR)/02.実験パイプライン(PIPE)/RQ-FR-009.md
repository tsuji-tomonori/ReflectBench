---
id: RQ-FR-009
title: 追加実験Aをeditとpredictの2段で実行できる
doc_type: 機能要求
phase: RQ
version: 1.0.2
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related:
  - '[[RQ-GL-014]]'
  - '[[RQ-GL-015]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-009
- 種別: 機能要求
- 優先度: MUST
- 要求: 実験Aを edit（Nova Micro）と predict（4 predictor）で実行できる。
- 要求（実験詳細プロファイル）: `.ai_workspace/llm-temp-introspection` 準拠で edit/predict の 2 段を実行し、[[RQ-GL-014|info-plus]] / [[RQ-GL-015|info-minus]] を出力できる。
- 根拠: POC と同じ比較構造を維持するため。
- 受入基準: `info_plus` と `info_minus` の予測結果が出力される。
- 例外/エラー: edit 出力不正時は invalid に退避する。
- 依存・関連: [[RQ-UC-003]]

## 変更履歴
- 2026-02-28: info-plus/info-minus 用語と実験詳細プロファイル受入基準を追記 [[RQ-RDR-002]]
- 2026-02-28: 実験Aのアプリモジュール追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
