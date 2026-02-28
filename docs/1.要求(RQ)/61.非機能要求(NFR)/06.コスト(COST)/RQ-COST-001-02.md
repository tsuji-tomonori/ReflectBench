---
id: RQ-COST-001-02
title: Qwen3 32B支配コストをphase別に追跡できる
doc_type: 非機能要求
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related:
  - '[[RQ-FR-014]]'
tags:
  - llm-temp-introspection
  - RQ
  - COST
---

## SnowCard（日本語）
- 要求ID: RQ-COST-001-02
- 種別: 非機能要求
- 優先度: SHOULD
- 要求: 本システムは、Qwen3 32B のコスト寄与を [[RQ-GL-003|phase]] 別に追跡できる。
- 根拠: 追加実験Dのコスト増加を早期に検知するため。
- 受入基準: [[RQ-GL-002|run]] [[RQ-GL-005|manifest]] で [[RQ-GL-003|phase]] 別件数とモデル内訳を確認できる。
- 例外/エラー: 一時的な試験[[RQ-GL-002|run]]は除外集計できる。
- 依存・関連: [[RQ-FR-014]]

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
