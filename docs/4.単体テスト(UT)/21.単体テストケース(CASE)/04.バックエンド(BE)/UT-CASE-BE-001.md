---
id: UT-CASE-BE-001
title: POST /runs 正常起動
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-API-001]]'
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
- 固定条件入力で [[RQ-GL-002|run]] 作成が受理されることを確認する。

## 前提
- durable 起動処理と S3 保存処理はモック化する。

## 手順
1. `loops=10`, `full_cross=true` を含む有効リクエストを送る。
2. API 応答を確認する。

## 期待結果
- `202 Accepted` を返す。
- `run_id`, `accepted_at`, `initial_phase`, `state=QUEUED` を返す。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
