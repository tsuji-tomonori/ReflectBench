---
id: UT-CASE-APP-004
title: strict JSON 正常検証
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
- 正常 JSON が `normalized/` へ保存されることを確認する。

## 手順
1. schema 準拠 JSON を入力する。

## 期待結果
- Pydantic 検証成功。
- `normalized/` へ変換データが保存される。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
