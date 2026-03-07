---
id: DD-APP-OVR-001
title: アプリ詳細設計総論
doc_type: アプリ詳細
phase: DD
version: 1.0.3
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-06'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-INF-OVR-001]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - DD
  - APP
---

## 詳細仕様
- アプリ詳細は「モジュール仕様 + API実装 + データ契約 + ログ/エラー」の4文書を正本として管理する。
- INF 詳細は durable 実行基盤と運用制約を扱い、アプリ詳細は入力検証・step 判定・整形ロジックを扱う。
- 実験ロジックの正本は `.ai_workspace/llm-temp-introspection/src/study/*.py` とし、Batch/Durable の制約は [[DD-INF-DEP-001]] 準拠とする。

## 正本境界
| 領域 | 正本文書 | 扱う内容 |
|---|---|---|
| モジュール責務 | [[DD-APP-MOD-001]] | use case 別の責務分離 |
| API 実装規約 | [[DD-APP-API-001]] | ハンドラ処理順・応答モデル |
| データモデル | [[DD-APP-DATA-001]] | Pydantic モデルと I/O 変換 |
| ログ/エラー | [[DD-APP-ERR-001]] | 失敗分類・再試行可否・監査キー |

## アプリ処理フロー
1. `run_api` が `POST /runs` を受け付け、構文検証 -> 業務検証 -> 競合検証の順で入力を検証する。
2. `idempotency_key` が既存 `run_id` と一致する場合は新規 durable 起動せず、既存 `run_id` を返す。
3. 新規受付時は `run_id` を発行し、`runs/{run_id}/config.json` を保存し、DynamoDB に `RunSummary(state=QUEUED)` を登録する。
4. `start_run` は `orchestrator_durable_fn:live` を `DurableExecutionName=run_id` で起動し、`durable_execution_arn` を projection に保存する。
5. durable orchestration は `step` / child context により Study1 -> Study2 -> 実験A -> 実験D -> report を同一 execution のまま前進させる。
6. Bedrock Batch の待機は `wait_for_condition` または durable `wait` で継続し、未完了時も Lambda の自己再起動は行わない。
7. `normalizer` が Batch output を strict JSON + Pydantic で検証し、不正データは `invalid/` へ分離する。
8. `report_builder` が `reports/*.csv`, `reports/run_manifest.json`, `reports/artifact_index.json` を生成する。
9. projection は `phase`, `step`, `progress`, `execution_name`, `durable_execution_arn`, `artifact_index_key` を更新する。
10. 最終状態を `SUCCEEDED` / `PARTIAL` / `FAILED` に遷移し、`GET /runs/{run_id}` で参照可能にする。

## 実験詳細プロファイル（.ai_workspace 正本）
- Study2 は `self_reflection` / `within_model` / `across_model` の3条件を扱う。
- 閾値は Study2 が `low<=0.2, high>=0.8`、実験A/D が `low<=0.5, high>=0.8` を既定とする。
- 追実験Aは edit -> predict の2段で、`info_plus` / `info_minus` を生成して判定する。
- 追実験Dは `blind`（ラベル非開示）と `wrong_label`（FACTUAL/CRAZY swap）を実行する。
- 実験詳細プロファイルで生成される `output/study2/summary.csv`, `output/analysis/*.csv`, `output/figures/*` は分析成果物として扱う。

### 責務境界（APP/INF）
- APP は入力検証、step 遷移判定、データ正規化、成果物整形のロジックを担当する。
- INF は durable 実行基盤、Batch 実行管理、IAM、監視、配備制約を担当する。
- DynamoDB は API/運用向け projection の正本であり、自前 scheduler 用 lease や cursor は保持しない。
- durable step 定義や運用パラメータの正本は [[DD-INF-DEP-001]] を参照し、本書はアプリ側の処理順と判定責務を正本とする。

## 受入条件
- RQ/BD から APP-DD へ辿れる reverse trace が成立している。
- INF-DD と APP-DD の責務重複がなく、参照境界が明確である。
- self-invoke や lease 前提なしで長時間 wait を継続できることが文書上も明確である。

## 変更履歴
- 2026-03-06: self-invoke / defer 前提を削除し、durable execution + projection 構成へ更新 [[DD-INF-DEP-001]]
- 2026-02-28: 実験詳細プロファイル（self/within/across, A/D 閾値）を追記 [[RQ-RDR-002]]
- 2026-02-28: アプリ処理フロー（受付-列挙-投入-poll-正規化-集計）と APP/INF 責務境界を追記 [[DD-INF-DEP-001]]
- 2026-02-28: 初版作成（APP詳細の正本境界を定義） [[BD-SYS-ADR-001]]
