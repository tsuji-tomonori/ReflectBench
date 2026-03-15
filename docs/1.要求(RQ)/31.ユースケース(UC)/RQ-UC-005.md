---
id: RQ-UC-005
title: 管理者が結果比較を行う
doc_type: ユースケース
phase: RQ
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-14'
up:
  - '[[RQ-SH-001]]'
related:
  - '[[RQ-FR-014]]'
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-020]]'
  - '[[RQ-RDR-005]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - UC
---

## シナリオ
1. [[RQ-SH-001|管理者]]が `GET /runs/{run_id}/results` または同結果から生成された report CSV を取得する。
2. システムは Batch 実行結果と direct rerun 補完結果を区別せず、同一 schema の正規化済み結果として返す。
3. 管理者が Study2 within/across と A/D の傾向を比較し、必要時のみ取得経路メタデータを監査する。

## 受入条件
- 比較に必要な出力項目が不足なく揃っている。
- 比較対象は DynamoDB 上の canonical result と S3 report で整合している。

## 変更履歴
- 2026-03-14: 結果比較の主経路を DynamoDB canonical result に変更 [[RQ-RDR-005]]
- 2026-02-28: 結果比較ユースケースのデータ契約追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 利用者統合方針に合わせ、実施主体を管理者へ変更 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
