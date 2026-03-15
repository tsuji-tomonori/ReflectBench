---
id: RQ-UC-004
title: 実験成果物を取得する
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
  - '[[RQ-FR-020]]'
  - '[[RQ-RDR-005]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - UC
---

## シナリオ
1. [[RQ-SH-001|管理者]]が `GET /runs/{run_id}/artifacts` を呼び出す。
2. システムが reports/raw/invalid など S3 監査成果物のキー一覧を返す。
3. 管理者は raw 出力や invalid の追跡に S3 成果物を使い、正規化済み結果の取得は `GET /runs/{run_id}/results` を使う。

## 受入条件
- 主要 report CSV と invalid/raw 監査成果物へ到達できる。
- canonical な正規化済み結果の取得経路と、S3 監査成果物の取得経路が区別されている。

## 変更履歴
- 2026-03-14: canonical result は results API、artifacts API は S3 監査成果物用とする役割分離を追記 [[RQ-RDR-005]]
- 2026-02-28: 成果物参照ユースケースの API 詳細追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
