---
id: UT-CASE-BE-006
title: GET /runs/{run_id}/artifacts 空応答
doc_type: 単体テストケース
phase: UT
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-11'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-API-001]]'
related:
  - '[[RQ-FR-004]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `GET /runs/{run_id}/artifacts`

## テスト目的
- 成果物未生成時でも成功応答と空配列を返すことを確認する。
- repair run の場合に `lineage` / `repair` が成果物APIへ含まれることを確認する。

## 手順
1. 成果物なし [[RQ-GL-002|run]] の artifacts API を呼ぶ。

## 期待結果
- `200 OK` を返す。
- `reports/normalized/invalid` は空配列で返る。

## 変更履歴
- 2026-03-11: repair run の lineage/repair 応答確認を追加 [[RQ-RDR-003]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
