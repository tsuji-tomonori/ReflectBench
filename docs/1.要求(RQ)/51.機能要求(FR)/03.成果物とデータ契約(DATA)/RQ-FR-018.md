---
id: RQ-FR-018
title: 正規化済み実験結果をDynamoDBへ保存できる
doc_type: 機能要求
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-14
updated: '2026-03-14'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-005]]'
  - '[[RQ-UC-007]]'
related:
  - '[[RQ-FR-011]]'
  - '[[RQ-FR-013]]'
  - '[[RQ-RDR-005]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-018
- 種別: 機能要求
- 優先度: MUST
- 要求: 正規化済み実験結果を DynamoDB `experiment_result_table` に保存し、`experiment_id`, `run_id`, prompt, normalized result, 取得経路メタデータを一元参照できる。
- 根拠: 最終分析と再現監査の入力を単一の canonical source に統一するため。
- 受入基準: strict JSON + schema 検証を通過した各結果が `experiment_id` を key に upsert され、同一 run の結果集合を DynamoDB から取得できる。
- 例外/エラー: schema 不整合や item 制約超過で保存できない結果は canonical result に含めず、raw/invalid 側に理由を残す。
- 依存・関連: [[RQ-UC-005]], [[RQ-UC-007]]

## 変更履歴
- 2026-03-14: 初版作成（DynamoDB canonical result 保存要件を追加） [[RQ-RDR-005]]
