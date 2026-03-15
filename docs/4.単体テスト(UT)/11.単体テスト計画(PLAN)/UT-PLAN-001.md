---
id: UT-PLAN-001
title: 単体テスト仕様書（run実行基盤）
doc_type: 単体テスト計画
phase: UT
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-13'
up:
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-APP-OVR-001]]'
related:
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-INF-IAM-001]]'
  - '[[DD-INF-MON-001]]'
  - '[[DD-INF-PIPE-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-014]]'
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-017]]'
  - '[[RQ-PS-001-01]]'
  - '[[RQ-OBS-001-01]]'
  - '[[RQ-SEC-001-01]]'
  - '[[UT-CASE-BE-001]]'
  - '[[UT-CASE-BE-002]]'
  - '[[UT-CASE-BE-003]]'
  - '[[UT-CASE-BE-004]]'
  - '[[UT-CASE-BE-005]]'
  - '[[UT-CASE-BE-006]]'
  - '[[UT-CASE-BE-007]]'
  - '[[UT-CASE-BE-008]]'
  - '[[UT-CASE-APP-001]]'
  - '[[UT-CASE-APP-002]]'
  - '[[UT-CASE-APP-003]]'
  - '[[UT-CASE-APP-004]]'
  - '[[UT-CASE-APP-005]]'
  - '[[UT-CASE-APP-006]]'
  - '[[UT-CASE-APP-007]]'
  - '[[UT-CASE-APP-008]]'
  - '[[UT-CASE-APP-009]]'
  - '[[UT-CASE-APP-010]]'
  - '[[UT-PW-001]]'
  - '[[UT-PW-BE-API-001]]'
  - '[[UT-PW-APP-ORCH-001]]'
  - '[[UT-PW-APP-DATA-001]]'
  - '[[UT-PW-APP-ERR-001]]'
  - '[[UT-PW-APP-MON-001]]'
  - '[[UT-TRC-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - UT
  - PLAN
---

## テスト目的
- `run` 制御API、durable orchestration、データ正規化、レポート生成の単体品質を保証する。
- DD-INF と DD-APP で分離した責務（契約/実装）を、モジュール単位で検証する。
- IT へ持ち越す不具合を「契約逸脱」「入力検証不備」「再試行制御不備」に限定する。

## 対象範囲
- API: `POST /runs`, `POST /runs/{run_id}/cancel`, `POST /runs/{run_id}/repairs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/artifacts`
- Orchestration: Study1 -> Study2(within/across) -> 実験A -> 実験D -> report の step 制御
- Data: strict JSON 検証、Pydantic 変換、`invalid/` 退避、`record_id` 生成
- Error/Log: `run_id` 相関ログ、`retryable` 判定、`RunStatus.last_error` 反映
- Metrics: `RunStarted/RunSucceeded/RunFailed/ShardRetryCount/ParseFailureCount/RunDurationSec`

## 非対象
- 実AWSへの結合動作（Bedrock/S3/API Gateway 実リソース連携）
- E2E シナリオ（運用手順全体）
- コスト実測の正確性評価（週次運用評価で実施）

## テスト設計方針
- 技法:
  - 同値分割/境界値: `loops`, `shard_size`, `poll_interval_sec`, `idempotency_key`
  - 状態遷移: `QUEUED -> RUNNING -> SUCCEEDED|FAILED|PARTIAL`, `QUEUED|RUNNING -> CANCELLING -> CANCELLED`
  - エラー推測: parse failure, Bedrock 一時失敗, timeout
  - ペアワイズ: 2-wise 組合せは [[UT-PW-001]] と `UT-PW-*` で管理する。
- モック方針:
  - AWS SDK（Bedrock/S3/CloudWatch）をモック化する。
  - 時刻・UUID・sha256 は固定シードで再現可能化する。
- データ方針:
  - 正常JSON、欠損JSON、型不一致JSON、長文出力JSONをテストデータ化する。
  - `record_id` は同一入力で同一値になる固定検証を実施する。

## 単体テストケース一覧
| ケースID | 対象 | 観点 | 入力 | 期待結果 |
|---|---|---|---|---|
| UT-CASE-BE-001 | `POST /runs` | 正常起動 | 固定条件入力 | `202` + `run_id` + `QUEUED` |
| UT-CASE-BE-002 | `POST /runs` | バリデーション | `loops != 10` | `400` |
| UT-CASE-BE-003 | `POST /runs` | 冪等 | 同一 `idempotency_key` 再送 | 同一 `run_id` |
| UT-CASE-BE-004 | `GET /runs/{run_id}` | 状態参照 | 既存 `run_id` | DynamoDB正本の `phase/state/progress/last_error` と `lineage/repair/cancel` を返す |
| UT-CASE-BE-005 | `GET /runs/{run_id}` | Not Found | 未知 `run_id` | `404` |
| UT-CASE-BE-006 | `GET /runs/{run_id}/artifacts` | 空応答 | 成果物未生成 | `200` + 空配列 |
| UT-CASE-BE-007 | `POST /runs/{run_id}/repairs` | repair 起動/検証 | 親run条件と repair 条件 | `202` または `409` |
| UT-CASE-BE-008 | `POST /runs/{run_id}/cancel` | 停止要求/冪等 | `RUNNING`, `CANCELLING`, `SUCCEEDED` | `202`, `200`, `409` |
| UT-CASE-APP-001 | orchestration | step遷移 | 正常step列 | 最終 `SUCCEEDED` |
| UT-CASE-APP-002 | orchestration | 部分失敗 | parse失敗混在 | `PARTIAL` + `invalid` 除外継続 |
| UT-CASE-APP-003 | retry制御 | [[RQ-GL-004|shard]] retry | 1回目失敗 -> 2回目成功 | retry回数が記録される |
| UT-CASE-APP-004 | data | strict JSON | 正常JSON | `normalized/` 保存 |
| UT-CASE-APP-005 | data | schema不一致 | 欠損JSON | `invalid/` 保存 |
| UT-CASE-APP-006 | data | deterministic ID | 同一条件2回 | 同一 `record_id` |
| UT-CASE-APP-007 | report | 成果物生成 | 正常records | 5 CSV + `run_manifest.json` |
| UT-CASE-APP-008 | metrics | 可観測性 | [[RQ-GL-002|run]]完了時 | 必須メトリクス送信 |
| UT-CASE-APP-009 | error model | 分類 | timeout/dependency | `category/retryable/step` 正常設定 |
| UT-CASE-APP-010 | orchestration | Bedrock Batch shard 境界 | `550 rows` / `2574 rows` / `74 rows` | 再配分または validation error |

## 品質ゲート
- 必須:
  - 全ケース成功率 100%
  - 重大ケース（API契約、state遷移、deterministic ID）は失敗ゼロ
- カバレッジ目標:
  - 行カバレッジ 85%以上
  - 分岐カバレッジ 75%以上
- 逸脱時:
  - UTレポートへ理由と是正期限を記録し、IT移行をブロックする。

## 実行手順
1. 単体テスト実行（アプリ）
2. カバレッジ計測
3. 静的解析（型・lint: `task app:check`）
4. docs整合チェック（`task docs:guard`）

## 完了条件
- `RQ-FR-001..017` の主要受入基準が UT ケースに対応付け済みである。
- `RQ-PS-001-01`, `RQ-OBS-001-01`, `RQ-SEC-001-01` の検証観点がケース化されている。
- 失敗時の再試行/部分成功/エラー記録の挙動が再現可能である。

## 変更履歴
- 2026-03-13: cancel API ケースと `CANCELLING/CANCELLED` 状態遷移を追加 [[RQ-FR-017]]
- 2026-03-12: Bedrock Batch shard 境界の UT ケースを追加し、完了条件の FR 範囲を更新 [[DD-INF-DEP-002]]
- 2026-02-28: 静的解析手順に `task app:check`（ruff + mypy）を追加 [[RQ-RDR-002]]
- 2026-02-28: UTトレーサビリティマトリクス（UT-TRC-001）を追加 [[RQ-RDR-002]]
- 2026-02-28: ペアワイズ設計文書（UT-PW）を追加し関連リンクを更新 [[RQ-RDR-002]]
- 2026-02-28: UTケース文書（BE/APP 15件）への追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成（DD-INF/DD-APP 分離後の単体テスト仕様を定義） [[RQ-RDR-002]]
