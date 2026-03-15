---
id: RQ-FR-013
title: deterministic experiment_id(record_id)で再処理を追跡できる
doc_type: 機能要求
phase: RQ
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-14'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-003]]'
related:
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-019]]'
  - '[[RQ-RDR-005]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-013
- 種別: 機能要求
- 優先度: MUST
- 要求: `sha256(...)` 生成の deterministic `experiment_id`（内部 `record_id` と同値）で再実行と重複排除を追跡できる。
- 根拠: retry 時の整合性を保つため。
- 受入基準: 同一条件再実行で同一 `experiment_id` が生成され、DynamoDB canonical result への upsert key として再利用される。
- 例外/エラー: キー項目欠落時は record 生成を中断する。
- 依存・関連: [[RQ-UC-003]]

## 変更履歴
- 2026-03-14: `experiment_id` を外部識別子として明示し、DynamoDB upsert key 用途を追加 [[RQ-RDR-005]]
- 2026-02-28: deterministic ID のデータ契約追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
