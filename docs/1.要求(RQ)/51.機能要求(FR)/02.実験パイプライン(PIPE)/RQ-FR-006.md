---
id: RQ-FR-006
title: Batch jobをshard単位で投入できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related:
  - '[[RQ-GL-004]]'
  - '[[RQ-GL-006]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-006
- 種別: 機能要求
- 優先度: MUST
- 要求: [[RQ-GL-004|shard]] 単位で `CreateModelInvocationJob` を発行できる。
- 根拠: 大量実行を安定して処理するため。
- 受入基準: [[RQ-GL-004|shard]] ごとに job_id が記録される。
- 例外/エラー: job 作成失敗時は再試行キューに移す。
- 依存・関連: [[RQ-GL-006]]

## 変更履歴
- 2026-02-28: Batch投入処理の DD-INF/DD-APP 追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
