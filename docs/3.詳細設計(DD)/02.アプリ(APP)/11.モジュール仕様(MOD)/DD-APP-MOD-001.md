---
id: DD-APP-MOD-001
title: 実験実行モジュール仕様
doc_type: モジュール仕様
phase: DD
version: 1.3.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-14'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-APP-OVR-001]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[RQ-FR-005]]'
  - '[[RQ-FR-006]]'
  - '[[RQ-FR-007]]'
  - '[[RQ-FR-008]]'
  - '[[RQ-FR-009]]'
  - '[[RQ-FR-010]]'
  - '[[RQ-FR-012]]'
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-016]]'
  - '[[RQ-FR-017]]'
  - '[[RQ-FR-018]]'
  - '[[RQ-FR-019]]'
  - '[[RQ-FR-020]]'
tags:
  - llm-temp-introspection
  - DD
  - APP
  - MOD
---

## 詳細仕様
- モジュールは `run_api`, `cancel_api`, `repair_api`, `results_api`, `orchestration`, `batch_adapter`, `normalizer`, `result_store`, `rerun_adapter`, `report_builder` に分割する。
- 各モジュールは pure logic を優先し、AWS 依存は adapter 境界に隔離する。
- 実験アルゴリズムの具体ロジックは `.ai_workspace/llm-temp-introspection/src/study/s2.py`, `experiment_a.py`, `experiment_d.py` を参照実装とする。

## モジュール責務
| モジュール | 主な責務 | 入力 | 出力 |
|---|---|---|---|
| `run_api` | `POST /runs`, `GET /runs`, `GET /runs/{run_id}` ハンドラ処理 | HTTP request | API response |
| `cancel_api` | `POST /runs/{run_id}/cancel` の受理と停止要求記録 | 対象 run ID, cancel request | `CANCELLING/CANCELLED` 応答 |
| `repair_api` | `POST /runs/{run_id}/repairs` と repair seed 固定化 | 親run ID, repair request | child run config, repair seed |
| `results_api` | `GET /runs/{run_id}/results` の query / paging / serializer | run ID, filters | canonical result page |
| `orchestration` | step 遷移、進捗更新、cancel guard | `RunConfig` | `RunStatus` |
| `batch_adapter` | Bedrock job 投入/取得/停止 | [[RQ-GL-005|manifest]] key | job status |
| `normalizer` | strict JSON 検証と schema 変換 | batch output | normalized/invalid |
| `result_store` | 正規化済み結果の DDB upsert / query | normalized record, prompt metadata | canonical result item |
| `rerun_adapter` | missing result の direct rerun | prompt payload, model metadata | runtime response |
| `report_builder` | CSV / `run_manifest.json` 生成 | canonical result items | reports keys |

## 処理順序
1. `run_api` が入力検証を実施し、`idempotency_key` が既存一致なら既存 `run_id` を返す。
2. 新規受付時のみ `run_id` 発行と `RunConfig` 保存を行い、`orchestration` 起動を要求する。
3. `orchestration` が Study1 列挙 -> Batch submit -> Job poll を進行し、都度 `batch_adapter` を呼び出す。
4. `normalizer` が出力を検証し、失敗レコードを `invalid/` へ分離する。
5. `result_store` が prompt / normalized result / source metadata を canonical result として upsert する。
6. `orchestration` が expected `experiment_id` と canonical result を比較し、欠損分だけ `rerun_adapter` で direct rerun する。
7. `orchestration` が Study2 within/across、実験A、実験D を順次進行し、各 phase で `normalizer -> result_store -> rerun_adapter` を繰り返す。
8. `report_builder` が canonical result から成果物を確定し、`RunStatus` を `SUCCEEDED/PARTIAL/FAILED` へ遷移する。
9. repair run では `repair_api` が対象 invalid を固定化し、`orchestration` は Study1 repair のみ、または `rebuild_downstream=true` 時に下流再構築を進行する。
10. cancel run では `cancel_api` が `CANCELLING` を記録し、`orchestration` は次の submit/poll/report 境界で cancel guard を評価して新規作業投入を止める。
11. `batch_adapter` が進行中 Batch job へ停止要求を発行し、外部ジョブ停止が確認できた時点で `RunStatus` を `CANCELLED` へ遷移する。

## 実験詳細ルール（.ai_workspace 準拠）
- Study2 は `self_reflection`（自己判定再利用）, `within_model`, `across_model` の3条件を区別する。
- `across_model` は generator と異なる predictor のみを対象にする。
- 実験Aは `PromptType.NORMAL` サンプルのみを edit 対象にし、`info_plus` / `info_minus` を予測する。
- 実験D `wrong_label` は `FACTUAL <-> CRAZY` swap のみを対象とし、`NORMAL` は除外する。
- Study1 / Study2 / 実験A の prompt 本文は `.ai_workspace/llm-temp-introspection/resources/prompts/*.txt` の日本語テンプレートに揃え、運用実装では `app/orchestrator/prompts.py` を正本とする。
- Study1 prompt 本文に実際の `temperature` 値を埋め込んではならない。Study2 / 実験D prompt 本文に `condition_type`（`blind`, `wrong_label` など）の内部ラベルを露出してはならない。
- Bedrock Batch へ投入する manifest は model/phase 単位で `100..shard_size` を満たすように再配分し、成立しない件数は validation error とする。
- direct rerun は Batch / repair と同一 prompt template と inference config を再利用し、取得経路だけが `acquired_via=direct_rerun` として区別される。
- cancel request を受理した run は `CANCELLING` 中に新規 Batch submit を行ってはならない。停止要求が通常完了と競合した場合は、先に確定した終端状態を優先する。
- repair run は `study1` の `invalid_only` に限定し、`renormalize` は parent invalid の raw 出力再正規化、`rerun` は child manifest 再投入で処理する。
- repair run の `rerun` は `repair_api` が seed 行件数を model 単位で検証し、親runの `shard_size` で Batch 制約を満たせない場合は child run を起動しない。

## 受入条件
- モジュール単位で単体テスト可能な責務分離になっている。
- retry 時に `orchestration` が同一 `record_id` で再処理できる。

## 変更履歴
- 2026-03-14: `results_api`、`result_store`、`rerun_adapter` を追加し、canonical result 中心の処理順へ更新 [[RQ-RDR-005]]
- 2026-03-13: `cancel_api`、cancel guard、Batch stop 責務を追加 [[RQ-FR-017]]
- 2026-03-12: Batch shard 再配分と repair rerun の事前検証を追記 [[DD-INF-DEP-002]]
- 2026-02-28: 実験詳細ルール（self条件、A/D対象条件）を追記 [[RQ-RDR-002]]
- 2026-03-11: `repair_api` と repair workflow / downstream rebuild 分岐を追記 [[RQ-RDR-003]]
- 2026-02-28: 総論のアプリ処理フローに合わせて処理順序を具体化（idempotency/retry/終状態遷移を明確化） [[DD-APP-OVR-001]]
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]実行ロジックのモジュール分割を定義） [[BD-SYS-ADR-001]]
