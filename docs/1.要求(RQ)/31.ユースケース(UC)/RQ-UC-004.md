---
id: RQ-UC-004
title: 実験成果物を取得する
doc_type: ユースケース
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SH-001]]'
related:
  - '[[RQ-FR-014]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - UC
---

## シナリオ
1. [[RQ-SH-001|管理者]]が `GET /runs/{run_id}/artifacts` を呼び出す。
2. システムが reports/normalized/invalid のキー一覧を返す。

## 受入条件
- 主要 report CSV へ到達できる。

## 変更履歴
- 2026-02-28: 成果物参照ユースケースの API 詳細追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
