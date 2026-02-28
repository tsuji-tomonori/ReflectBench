---
id: UT-CASE-APP-001
title: orchestration 正常step遷移
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
  - '[[RQ-FR-005]]'
  - '[[RQ-FR-010]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `orchestration`

## テスト目的
- 全stepを正常遷移し最終成功状態となることを確認する。

## 手順
1. 各step成功を返すモックで [[RQ-GL-002|run]] 実行する。

## 期待結果
- 状態遷移が順序どおり進行する。
- 最終 `SUCCEEDED` となる。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
