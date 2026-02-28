---
id: UT-CASE-APP-007
title: レポート成果物生成
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
  - '[[RQ-FR-014]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `report_builder`

## テスト目的
- 必須成果物6種が生成されることを確認する。

## 手順
1. 正常な normalized records を入力して report 生成する。

## 期待結果
- 5 CSV + `run_manifest.json` が出力される。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
