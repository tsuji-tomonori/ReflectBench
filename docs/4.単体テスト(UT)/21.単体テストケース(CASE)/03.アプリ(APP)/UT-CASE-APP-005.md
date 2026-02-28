---
id: UT-CASE-APP-005
title: schema不一致時のinvalid退避
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-APP-DATA-001]]'
related:
  - '[[RQ-FR-011]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `normalizer`

## テスト目的
- schema 不一致時に `invalid/` 退避されることを確認する。

## 手順
1. 必須欠損 JSON を入力する。

## 期待結果
- 検証失敗となる。
- `invalid/` へ保存される。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
