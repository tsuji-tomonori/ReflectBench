---
id: RQ-FR-016
title: repair runの親子関係と再構築範囲を追跡できる
doc_type: 機能要求
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-11
updated: '2026-03-11'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-003]]'
related:
  - '[[RQ-FR-002]]'
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-004]]'
  - '[[RQ-FR-013]]'
  - '[[BD-SYS-ADR-002]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-016
- 種別: 機能要求
- 優先度: MUST
- 要求: repair run について `parent_run_id`、`repair_phase`、`repair_scope`、`repair_mode`、`rebuild_downstream`、`source_invalid_keys` を保存し、状態/成果物APIから追跡できる。
- 根拠: 親runを不変に保ちつつ、どの invalid をどう復旧したかを監査可能にするため。
- 受入基準: `GET /runs/{repair_run_id}` で親run参照と repair 条件が分かり、`GET /runs/{repair_run_id}/artifacts` で repair 成果物を元runと分離して参照できる。
- 例外/エラー: repair 中に下流再構築が失敗した場合も、親runの既存成果物は変更しない。
- 依存・関連: [[RQ-UC-003]]

## 変更履歴
- 2026-03-11: 初版作成（repair runの系譜・差分追跡要件を追加） [[RQ-RDR-003]]
