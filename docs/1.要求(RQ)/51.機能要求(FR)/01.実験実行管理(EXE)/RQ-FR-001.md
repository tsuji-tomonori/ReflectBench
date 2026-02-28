---
id: RQ-FR-001
title: run作成APIで実験実行を開始できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-001]]'
related:
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-001
- 種別: 機能要求
- 優先度: MUST
- 要求: [[RQ-SH-001|管理者]]が `POST /runs` で実験実行を開始できる。
- 根拠: 実験起動をAPIで統一し再現性を確保するため。
- 受入基準: `202 Accepted` と `run_id` が返る。
- 例外/エラー: 必須入力不足時はバリデーションエラーを返す。
- 依存・関連: [[RQ-UC-001]]

## 変更履歴
- 2026-02-28: API契約の正本分離に合わせ DD-INF/DD-APP 逆リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
