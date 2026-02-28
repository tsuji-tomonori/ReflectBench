---
id: UT-CASE-APP-003
title: shard retry 制御
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-DEP-002]]'
related:
  - '[[RQ-FR-012]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `batch_adapter` / retry policy

## テスト目的
- [[RQ-GL-004|shard]] 単位で1回再試行されることを確認する。

## 手順
1. 1回目失敗、2回目成功のモックで実行する。

## 期待結果
- retry が1回だけ実行される。
- retry 件数が状態へ記録される。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
