---
id: RQ-FR-007
title: durable実行で長時間待機を処理できる
doc_type: 機能要求
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related:
  - '[[RQ-GL-007]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-007
- 種別: 機能要求
- 優先度: MUST
- 要求: `GetModelInvocationJob` の完了待ちを durable state で保持できる。
- 根拠: 15分制約を超える [[RQ-GL-002|run]] を扱うため。
- 受入基準: poll 中断後も [[RQ-GL-003|phase]] 進行が継続できる。
- 例外/エラー: timeout 超過時は失敗理由を記録して停止する。
- 依存・関連: [[RQ-GL-007]]

## 変更履歴
- 2026-02-28: durable待機処理の DD-INF/DD-APP 追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
