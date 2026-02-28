---
id: UT-CASE-BE-003
title: POST /runs 冪等性
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-APP-API-001]]'
related:
  - '[[RQ-FR-001]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `POST /runs`

## テスト目的
- 同一 `idempotency_key` 再送で重複起動しないことを確認する。
- 同一 `idempotency_key` かつ異なる payload は `409` で拒否されることを確認する。

## 手順
1. 同一 payload + 同一 `idempotency_key` で2回送信する。
2. 異なる payload + 同一 `idempotency_key` で送信する。

## 期待結果
- 2回目も `202` を返す。
- 1回目と同一 `run_id` を返す。
- 異なる payload では `409 Conflict` を返す。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
