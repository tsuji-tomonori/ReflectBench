---
id: RQ-RDR-005
title: 実験結果の正本はDynamoDBに一元化する
doc_type: 要求決定記録
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-14
updated: '2026-03-14'
up:
  - '[[RQ-DG-001]]'
related:
  - '[[RQ-UC-004]]'
  - '[[RQ-UC-005]]'
  - '[[RQ-UC-007]]'
  - '[[RQ-FR-013]]'
  - '[[RQ-FR-014]]'
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-019]]'
  - '[[RQ-FR-020]]'
  - '[[BD-SYS-ADR-003]]'
  - '[[BD-INF-DEP-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - RDR
---

## 決定
- 正規化済み実験結果の正本は S3 `normalized/` ではなく DynamoDB `experiment_result_table` とする。
- `experiment_id` は既存の deterministic `record_id` と同値の外部識別子とし、`run_id` と組み合わせて結果行を一意に識別する。
- Batch 実行後は S3 上の raw output / normalized mirror を解析し、正規化済み結果を DynamoDB へ投入する。
- DynamoDB に存在しない期待結果は、同一 prompt とメタデータで Bedrock Runtime を直接呼び出して補完し、正規化後に同じ DynamoDB へ投入する。
- 最終レポート生成と結果取得 API は DynamoDB 上の正規化済み結果を参照し、Batch 実行か direct rerun かで集計経路を分岐しない。
- S3 は manifest、batch-output、invalid、report、監査用 mirror の保存先として継続利用する。

## 根拠
- 最終成果物に必要なのは「全ての実験結果が揃っていること」であり、取得経路は要件上の本質ではないため。
- `invalid/` の存在と最終レポートの完全性を切り離し、Batch 側の一時的不整合を direct rerun で吸収した方が運用が単純になるため。
- 比較分析と再現調査では、run 単位で prompt / normalized result / 取得経路メタデータを一元参照できる方が扱いやすいため。

## トレードオフ
- DynamoDB に prompt と正規化済み結果を保持するため、projection 専用構成よりストレージ費と item 設計の制約が増える。
- `normalized/` は正本ではなく mirror になるため、既存の S3 中心の参照手順は結果 API 中心へ更新が必要になる。
- 補完 rerun を自動化すると成功率は上がる一方、run 完了までの所要時間と Bedrock Runtime 呼び出し数は増える。

## 影響
- `GET /runs/{run_id}/results` を追加し、管理者は DynamoDB の canonical result を API で取得する。
- `report_builder` は S3 `normalized/` ではなく DynamoDB `experiment_result_table` を入力に CSV / `run_manifest.json` を生成する。
- run の `SUCCEEDED/PARTIAL` 判定は `invalid/` 件数ではなく、期待 `experiment_id` が DynamoDB に揃ったかどうかで決める。
- `RQ-FR-018`、`RQ-FR-019`、`RQ-FR-020`、`BD-SYS-ADR-003`、DD-INF/DD-APP 文書群を追加・更新する。

## 変更履歴
- 2026-03-14: 初版作成（実験結果の canonical source を DynamoDB に移し、補完 rerun と結果 API を要求化） [[RQ-RDR-005]]
