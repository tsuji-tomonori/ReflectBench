---
id: RQ-FR-002
title: run設定をS3へ保存して追跡できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-001]]'
related:
  - '[[RQ-GL-002]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-002
- 種別: 機能要求
- 優先度: MUST
- 要求: `runs/{run_id}/config.json` を保存し、再実行判断に利用できる。
- 根拠: 実行設定の監査可能性が必要なため。
- 受入基準: config が保存され、status APIから参照できる。
- 例外/エラー: 保存失敗時は [[RQ-GL-002|run]] 開始を中断する。
- 依存・関連: [[RQ-UC-001]]

## 変更履歴
- 2026-02-28: [[RQ-GL-002|run]]設定保存のデータ契約追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
