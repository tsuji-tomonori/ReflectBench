---
id: RQ-UC-002
title: 実行状態を確認する
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
  - '[[RQ-FR-003]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - UC
---

## シナリオ
1. [[RQ-SH-001|管理者]]が `GET /runs/{run_id}` を呼び出す。
2. システムが `phase`, `state`, `progress`, `last_error` を返す。

## 受入条件
- 進捗情報が [[RQ-GL-003|phase]] 単位で参照できる。

## 変更履歴
- 2026-02-28: status 参照ユースケースの API 詳細追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
