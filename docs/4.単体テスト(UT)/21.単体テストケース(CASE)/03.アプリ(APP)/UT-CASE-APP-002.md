---
id: UT-CASE-APP-002
title: orchestration 部分失敗継続
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-APP-MOD-001]]'
related:
  - '[[RQ-FR-012]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `orchestration`

## テスト目的
- parse failure 混在時に `PARTIAL` で継続完走することを確認する。

## 手順
1. 一部レコードのみ parse failure を返すデータで実行する。

## 期待結果
- `invalid/` へ退避される。
- 集計は継続し最終 `PARTIAL` となる。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
