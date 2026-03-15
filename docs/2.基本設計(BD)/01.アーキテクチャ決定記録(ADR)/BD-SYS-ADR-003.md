---
id: BD-SYS-ADR-003
title: 実験結果の正本はDynamoDB canonical result tableを採用
doc_type: アーキテクチャ決定記録
phase: BD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-14
updated: '2026-03-14'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[RQ-RDR-005]]'
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-019]]'
  - '[[RQ-FR-020]]'
  - '[[BD-SYS-ADR-001]]'
  - '[[BD-SYS-ADR-002]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-IAM-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - BD
  - ADR
---

## 決定
- `run_control_table` とは別に `experiment_result_table` を追加し、正規化済み実験結果の canonical source とする。
- `experiment_result_table` には `experiment_id(=record_id)`, `run_id`, prompt payload, normalized result, source metadata を保存する。
- Batch は主経路として継続利用するが、canonical result が不足した場合は Bedrock Runtime 直呼び出しで補完する。
- report 生成と result API は `experiment_result_table` を入力にし、S3 `normalized/` は監査用 mirror とみなす。
- S3 は manifest / batch-output / invalid / reports の保存先として残し、raw と canonical を役割分離する。

## 根拠
- 最終レポートの完全性を、Batch の成功率ではなく canonical result の充足率で管理したいため。
- S3 JSONL のみを正本にすると、補完 rerun 後の集計経路が二重化し、分析入力が不安定になるため。
- DynamoDB を正本に寄せると、run 単位 API と再処理監査を同一 key 設計で扱えるため。

## トレードオフ
- `experiment_result_table` の設計、GSI、item サイズ制約、IAM 権限が追加で必要になる。
- raw artifact と canonical result の二重保持になるため、データ整合チェックを明示的に設計する必要がある。
- `invalid/` が残っても backfill 完了なら `SUCCEEDED` になり得るため、従来の「invalid 件数 = 完了品質」の理解は更新が必要になる。

## 影響
- `GET /runs/{run_id}/results` を新設し、管理者の主参照系 API を S3 artifact から DynamoDB result store へ移す。
- Orchestrator に S3->DynamoDB ingest と missing-result backfill を追加する。
- IAM に direct rerun 用 Bedrock Runtime 権限と `experiment_result_table` 読み書き権限を追加する。
- `run_manifest.json` に backfill 件数、canonical result 件数、未充足件数を記録する。

## 変更履歴
- 2026-03-14: 初版作成（DynamoDB canonical result table と direct rerun backfill 方針を記録） [[RQ-RDR-005]]
