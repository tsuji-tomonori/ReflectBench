---
id: DD-APP-OVR-001
title: アプリ詳細設計総論
doc_type: アプリ詳細
phase: DD
version: 1.0.2
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-01'
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
- INF 詳細は実行基盤と運用制約を扱い、アプリ詳細は入力検証・状態遷移・整形ロジックを扱う。
- 実験ロジックの正本は `.ai_workspace/llm-temp-introspection/src/study/*.py` とし、INF の基盤制約（Batch/Durable）は `plan.md` 準拠を維持する。

## 正本境界
| 領域 | 正本文書 | 扱う内容 |
|---|---|---|
| モジュール責務 | [[DD-APP-MOD-001]] | use case 別の責務分離 |
| API 実装規約 | [[DD-APP-API-001]] | ハンドラ処理順・応答モデル |
| データモデル | [[DD-APP-DATA-001]] | Pydantic モデルと I/O 変換 |
| ログ/エラー | [[DD-APP-ERR-001]] | 失敗分類・再試行可否・監査キー |

## アプリ処理フロー
1. `run_api` が `POST /runs` を受け付け、構文検証 -> 業務検証 -> 競合検証の順で入力を検証する。
2. `idempotency_key` が既存 `run_id` と一致する場合は新規起動せず、既存 `run_id` を返す。
3. 新規受付時は `run_id` を発行し、`RunConfig` を保存して durable 起動要求を登録する。
4. `orchestration` が step を開始し、Study1 列挙（6,600 records）で初期 [[RQ-GL-005|manifest]] を確定する。
5. `batch_adapter` が [[RQ-GL-004|shard]] 単位で Batch job を投入し、job 状態を `RunStatus` に反映する。
6. `orchestration` が job 状態を1回確認し、未完了時は同一 phase のまま defer して次 invocation で継続する。
7. `normalizer` が Batch output を strict JSON + Pydantic で検証し、不正データは `invalid/` へ分離する。
8. `orchestration` が Study2 候補を生成し、within -> across -> 実験A -> 実験D を順次実行する。
9. `report_builder` が `reports/*.csv` と `reports/run_manifest.json` を生成し、成果物キーを確定する。
10. 最終状態を `SUCCEEDED` または `FAILED` に遷移し、`GET /runs/{run_id}` で参照可能にする。

## 実験詳細プロファイル（.ai_workspace 正本）
- Study2 は `self_reflection` / `within_model` / `across_model` の3条件を扱う。
- 閾値は Study2 が `low<=0.2, high>=0.8`、実験A/D が `low<=0.5, high>=0.8` を既定とする。
- 追実験Aは edit -> predict の2段で、`info_plus` / `info_minus` を生成して判定する。
- 追実験Dは `blind`（ラベル非開示）と `wrong_label`（FACTUAL/CRAZY swap）を実行する。
- 実験詳細プロファイルで生成される `output/study2/summary.csv`, `output/analysis/*.csv`, `output/figures/*` は分析成果物として扱う。

### 責務境界（APP/INF）
- APP は入力検証、状態遷移判定、データ正規化、成果物整形のロジックを担当する。
- INF は durable 実行基盤、Batch 実行管理、監視/IAM/配備制約を担当する。
- durable step 定義や運用パラメータの正本は [[DD-INF-DEP-001]] を参照し、本書はアプリ側の処理順と判定責務を正本とする。

## 受入条件
- RQ/BD から APP-DD へ辿れる reverse trace が成立している。
- INF-DD と APP-DD の責務重複がなく、参照境界が明確である。

## 変更履歴
- 2026-03-01: poll フローを non-blocking 化（1回確認 + defer）へ更新 [[DD-INF-DEP-001]]
- 2026-02-28: 実験詳細プロファイル（self/within/across, A/D 閾値）を追記 [[RQ-RDR-002]]
- 2026-02-28: アプリ処理フロー（受付-列挙-投入-poll-正規化-集計）と APP/INF 責務境界を追記 [[DD-INF-DEP-001]]
- 2026-02-28: 初版作成（APP詳細の正本境界を定義） [[BD-SYS-ADR-001]]
