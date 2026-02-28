---
id: UT-CASE-APP-006
title: deterministic record_id 生成
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-DATA-001]]'
related:
  - '[[RQ-FR-013]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `record_id` 生成関数

## テスト目的
- 同一条件で同一 ID が生成されることを確認する。

## 手順
1. 同一入力で2回ID生成する。

## 期待結果
- 2回とも同じ `record_id` になる。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
