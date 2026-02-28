---
id: RQ-FR-014
title: レポートCSVとrun manifestを出力できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-004]]'
  - '[[RQ-UC-005]]'
related:
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
- 要求: `study1_summary.csv`, `study2_within.csv`, `study2_across.csv`, `experiment_a.csv`, `experiment_d.csv`, `run_manifest.json` を出力できる。
- 根拠: 比較分析と監査記録を両立するため。
- 受入基準: [[RQ-GL-002|run]] 完了時に6成果物が S3 に存在する。
- 例外/エラー: 失敗 [[RQ-GL-002|run]] では欠損理由を [[RQ-GL-002|run]]_[[RQ-GL-005|manifest]] に記録する。
- 依存・関連: [[RQ-UC-004]], [[RQ-UC-005]]

## 変更履歴
- 2026-02-28: 成果物契約の DD-INF/DD-APP 追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
