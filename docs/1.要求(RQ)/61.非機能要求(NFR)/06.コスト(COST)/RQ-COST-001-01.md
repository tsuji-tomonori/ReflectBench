---
id: RQ-COST-001-01
title: 1runの推定モデル費を3.50USD以下に維持できる
doc_type: 非機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related:
  - '[[RQ-PC-001]]'
  - '[[BD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - COST
---

## SnowCard（日本語）
- 要求ID: RQ-COST-001-01
- 種別: 非機能要求
- 優先度: MUST
- 要求: 本システムは、コスト最小化を最優先とし、標準条件の1[[RQ-GL-002|run]]推定モデル費を3.50USD以下に維持できる。
- 根拠: 実験成立に必要な最小費用で運用する制約（[[RQ-PC-001]]）を満たすため。
- 受入基準: 週次試算で1[[RQ-GL-002|run]]平均3.50USD以下を確認できる。
- 例外/エラー: モデル単価改定時は閾値を再評価できる。
- 依存・関連: [[BD-INF-DEP-001]]

## 変更履歴
- 2026-02-28: コスト要件の DD-INF/DD-APP 追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: コスト最小化を最優先とする制約を追記 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
