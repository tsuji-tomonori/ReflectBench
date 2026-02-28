---
id: RQ-SH-001
title: 管理者
doc_type: ステークホルダー
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related:
  - '[[RQ-UC-001]]'
  - '[[RQ-PC-001]]'
  - '[[RQ-PP-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - SH
---

## 責務
- 実験設定、実行、障害復旧、結果公開の最終意思決定を担う。
- `ap-southeast-2` の運用設定、Bedrock model routing、コスト管理を維持する。
- 本プロジェクトの唯一の利用者として、結果比較と評価も実施する。

## 関与範囲
- 要求定義: [[RQ-SC-001]]
- 実行運用: [[OPSREL-RUN-001]]

## 変更履歴
- 2026-02-28: 利用者を管理者へ一本化する制約を反映 [[RQ-RDR-002]]
- 2026-02-28: 初版作成（管理者責務を定義） [[RQ-RDR-002]]
