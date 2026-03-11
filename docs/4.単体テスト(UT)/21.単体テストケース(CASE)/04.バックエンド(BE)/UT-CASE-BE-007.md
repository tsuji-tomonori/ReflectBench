---
id: UT-CASE-BE-007
title: POST /runs/{run_id}/repairs 起動と検証
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-11
updated: '2026-03-11'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
related:
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-016]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `POST /runs/{run_id}/repairs`

## テスト目的
- 親run終端 + 対象 invalid ありのとき child repair run が受理されることを確認する。
- 親run未終端、対象 invalid 不在、重複 repair 要求が `409` で拒否されることを確認する。

## 前提
- 親runの config / manifest / invalid はモック化する。
- durable 起動処理と child run 保存処理はモック化する。

## 手順
1. `phase=study1`, `scope=invalid_only`, `mode=rerun` で repair API を呼ぶ。
2. 親run未終端、対象 invalid 不在、重複 repair 要求でも呼ぶ。

## 期待結果
- 正常系は `202 Accepted` を返す。
- child `run_id`, `lineage.parent_run_id`, `repair.source_invalid_keys` を返す。
- 異常系は `409 Conflict` を返す。

## 変更履歴
- 2026-03-11: 初版作成 [[RQ-RDR-003]]
