---
id: RQ-FR-019
title: 不足実験結果を自動再実行で補完できる
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
  - '[[RQ-FR-018]]'
  - '[[RQ-RDR-005]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-019
- 種別: 機能要求
- 優先度: MUST
- 要求: Batch 後に期待 `experiment_id` と DynamoDB canonical result を照合し、不足分を同一 prompt / メタデータで direct rerun して補完できる。
- 根拠: Batch 実行の一部失敗を raw 成果物に閉じ込め、最終レポートでは完全な結果集合を優先するため。
- 受入基準: 各 phase で canonical result の充足確認が行われ、不足があれば direct rerun 後に DynamoDB へ追加保存される。
- 受入基準（終状態）: backfill 後に期待結果が揃えば `SUCCEEDED`、不足が残れば `PARTIAL` とし、未充足件数を `run_manifest.json` に記録する。
- 例外/エラー: 同一条件の direct rerun が所定回数で成功しない場合は無限再試行せず、不足件数と理由を監査情報へ残す。
- 依存・関連: [[RQ-UC-005]], [[RQ-UC-007]]

## 変更履歴
- 2026-03-14: 初版作成（結果欠損の自動補完要件を追加） [[RQ-RDR-005]]
