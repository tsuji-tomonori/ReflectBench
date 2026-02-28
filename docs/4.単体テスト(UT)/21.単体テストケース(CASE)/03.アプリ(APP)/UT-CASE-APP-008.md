---
id: UT-CASE-APP-008
title: runメトリクス送信
doc_type: 単体テストケース
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
  - '[[DD-INF-MON-001]]'
related:
  - '[[RQ-OBS-001-01]]'
tags:
  - llm-temp-introspection
  - UT
  - CASE
---

## 対象
- metrics publisher

## テスト目的
- [[RQ-GL-002|run]] 完了時に必須メトリクスが送信されることを確認する。

## 手順
1. [[RQ-GL-002|run]] 成功イベントを発火する。

## 期待結果
- `RunStarted/RunSucceeded/RunDurationSec` が送信される。

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
