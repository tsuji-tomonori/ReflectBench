---
id: RQ-UC-007
title: 正規化済み実験結果を取得する
doc_type: ユースケース
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-14
updated: '2026-03-14'
up:
  - '[[RQ-SH-001]]'
related:
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-020]]'
  - '[[RQ-RDR-005]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - UC
---

## シナリオ
1. [[RQ-SH-001|管理者]]が `GET /runs/{run_id}/results` を呼び出し、必要に応じて `phase` や `experiment_id` で絞り込む。
2. システムが DynamoDB `experiment_result_table` を参照し、prompt、正規化済み戻り値、取得経路メタデータを返す。
3. 管理者は同一 run の結果を、Batch 実行分と direct rerun 分を意識せずに比較・分析へ利用する。

## 受入条件
- `run_id` 単位で正規化済み実験結果をページング取得できる。
- `experiment_id` ごとに prompt と normalized result が追跡できる。
- 取得経路は監査用に参照できるが、分析処理は取得経路差分に依存しない。

## 変更履歴
- 2026-03-14: 初版作成（DynamoDB canonical result の取得ユースケースを追加） [[RQ-RDR-005]]
