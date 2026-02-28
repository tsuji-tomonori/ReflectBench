---
id: RQ-FR-012
title: job失敗時にshard単位で再試行できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-003]]'
related:
  - '[[DD-INF-DEP-002]]'
  - '[[DD-INF-MON-001]]'
  - '[[DD-APP-ERR-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-012
- 種別: 機能要求
- 優先度: MUST
- 要求: Bedrock job failure 時に [[RQ-GL-004|shard]] 単位で1回再試行できる。
- 根拠: 部分失敗時の完走率を高めるため。
- 受入基準: 再試行履歴が [[RQ-GL-002|run]] status に記録される。
- 例外/エラー: 再試行後も失敗した [[RQ-GL-004|shard]] は失敗として記録する。
- 依存・関連: [[RQ-UC-003]]

## 変更履歴
- 2026-02-28: 再試行要件の監視/エラー設計追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
