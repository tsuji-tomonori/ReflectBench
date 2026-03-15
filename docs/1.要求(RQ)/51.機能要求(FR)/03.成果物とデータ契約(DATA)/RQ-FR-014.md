---
id: RQ-FR-014
title: DynamoDB正本からレポートCSVとrun manifestを出力できる
doc_type: 機能要求
phase: RQ
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-14'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-004]]'
  - '[[RQ-UC-005]]'
related:
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-019]]'
  - '[[RQ-FR-020]]'
  - '[[RQ-RDR-005]]'
  - '[[OPSREL-RUN-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-014
- 種別: 機能要求
- 優先度: MUST
- 要求: `study1_summary.csv`, `study2_within.csv`, `study2_across.csv`, `experiment_a.csv`, `experiment_d.csv`, `run_manifest.json` を、DynamoDB canonical result を入力に出力できる。
- 要求（実験詳細プロファイル）: `.ai_workspace/llm-temp-introspection` 準拠の `output/study2/summary.csv`、`output/analysis/*.csv`、`output/figures/*` を追加成果物として扱える。
- 根拠: 比較分析と監査記録を両立するため。
- 受入基準: [[RQ-GL-002|run]] 完了時に6成果物が S3 に存在し、CSV / `run_manifest.json` の件数が DynamoDB `experiment_result_table` と整合する。
- 受入基準（実験詳細プロファイル）: `experiment_a_p_high_delta.csv`, `experiment_d_accuracy_by_label_condition.csv`, `experiment_d_wrong_label_shift.csv` が生成される。
- 例外/エラー: backfill 後も不足が残る [[RQ-GL-002|run]] では欠損理由と未充足 `experiment_id` 件数を `run_manifest.json` に記録する。
- 依存・関連: [[RQ-UC-004]], [[RQ-UC-005]]

## 変更履歴
- 2026-03-14: レポート生成入力を DynamoDB canonical result に変更し、件数整合要件を追加 [[RQ-RDR-005]]
- 2026-02-28: 実験詳細プロファイル向け分析成果物を追記 [[RQ-RDR-002]]
- 2026-02-28: 成果物契約の DD-INF/DD-APP 追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
