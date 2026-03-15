---
id: UT-CASE-BE-008
title: POST /runs/{run_id}/cancel 停止要求と冪等性
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-13
updated: '2026-03-13'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
related:
  - '[[RQ-FR-017]]'
  - '[[RQ-FR-003]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `POST /runs/{run_id}/cancel`

## テスト目的
- `QUEUED/RUNNING` run に対する停止要求が `CANCELLING` として受理されることを確認する。
- `CANCELLING/CANCELLED` への再要求が冪等成功になることを確認する。
- `SUCCEEDED/FAILED/PARTIAL` への停止要求が `409` で拒否されることを確認する。

## 前提
- DynamoDB 上の run 状態はモック化する。
- durable 停止要求と Batch 停止要求の発行はモック化する。

## 手順
1. `state=RUNNING` の run に対して cancel API を呼ぶ。
2. 同じ run を `state=CANCELLING`、`state=CANCELLED` にして再度呼ぶ。
3. `state=SUCCEEDED` の run でも呼ぶ。

## 期待結果
- `RUNNING` では `202 Accepted` と `state=CANCELLING` を返す。
- `CANCELLING/CANCELLED` では `200 OK` と現在の `cancel` 情報を返す。
- `SUCCEEDED` では `409 Conflict` を返す。

## 変更履歴
- 2026-03-13: 初版作成（cancel API の受理・冪等性・競合を追加） [[RQ-FR-017]]
