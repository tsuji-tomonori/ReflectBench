---
id: UT-CASE-BE-002
title: POST /runs バリデーション異常
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-APP-API-001]]'
related:
  - '[[RQ-FR-001]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- `POST /runs`

## テスト目的
- 固定制約違反時に入力エラーとなることを確認する。

## 手順
1. `loops=9` でリクエストを送る。

## 期待結果
- `400 Bad Request` を返す。
- 制約違反のエラーコード/理由を返す。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
