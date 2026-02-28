---
id: UT-CASE-BE-005
title: GET /runs/{run_id} Not Found
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
  - '[[RQ-FR-003]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `GET /runs/{run_id}`

## テスト目的
- 未知 `run_id` のときに Not Found を返すことを確認する。

## 手順
1. 不存在 `run_id` を指定して呼び出す。

## 期待結果
- `404 Not Found` を返す。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
