---
id: UT-CASE-APP-009
title: エラー分類とretryable判定
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-APP-ERR-001]]'
related:
  - '[[RQ-OBS-001-01]]'
  - '[[RQ-SEC-001-01]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- error mapper

## テスト目的
- エラー分類と `retryable` が規約どおり設定されることを確認する。

## 手順
1. `timeout` / `dependency` / `validation` の各例外を入力する。

## 期待結果
- `category`, `retryable`, `step`, `trace_id` が正しく設定される。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
