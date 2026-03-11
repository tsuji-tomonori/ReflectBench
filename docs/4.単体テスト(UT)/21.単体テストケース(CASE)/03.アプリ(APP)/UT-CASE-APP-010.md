---
id: UT-CASE-APP-010
title: Bedrock Batch shard 境界と再配分
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-12
updated: '2026-03-12'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-DEP-002]]'
related:
  - '[[RQ-FR-006]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `orchestration` / manifest writer

## テスト目的
- Bedrock Batch 投入対象 [[RQ-GL-004|shard]] が `100..500 records` を満たすよう再配分されることを確認する。
- 再配分不能な件数が Bedrock submit 前に validation error となることを確認する。

## 手順
1. `550 rows`, `shard_size=500` で shard writer を実行する。
2. `2574 rows`, `shard_size=500` の追加実験A予測 manifest を生成する。
3. `74 rows`, `shard_size=500` で Batch 対象 manifest を生成する。

## 期待結果
- `550 rows` は `275 + 275` へ再配分される。
- `2574 rows` は `429 x 6` へ再配分される。
- `74 rows` は Bedrock submit 前に validation error となる。

## 変更履歴
- 2026-03-12: 初版作成 [[DD-INF-DEP-002]]
