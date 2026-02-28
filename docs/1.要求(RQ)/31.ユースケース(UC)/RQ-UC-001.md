---
id: RQ-UC-001
title: 実験実行を開始する
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
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-002]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - UC
---

## シナリオ
1. [[RQ-SH-001|管理者]]が `POST /runs` を実行する。
2. システムが入力検証し、`run_id` を返す。
3. [[RQ-GL-007|durable execution]] が開始される。

## 受入条件
- `202 Accepted` と `run_id` が返る。

## 変更履歴
- 2026-02-28: [[RQ-GL-002|run]]開始ユースケースの API 詳細追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
