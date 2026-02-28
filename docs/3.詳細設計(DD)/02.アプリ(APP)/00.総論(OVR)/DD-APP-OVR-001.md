---
id: DD-APP-OVR-001
title: アプリ詳細設計総論
doc_type: アプリ詳細
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
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
4. `orchestration` が step を開始し、Study1 列挙（6,600 records）で初期 manifest を確定する。
5. `batch_adapter` が shard 単位で Batch job を投入し、job 状態を `RunStatus` に反映する。
6. `orchestration` が poll 待機を継続し、完了まで step/state/progress を更新する。
7. `normalizer` が Batch output を strict JSON + Pydantic で検証し、不正データは `invalid/` へ分離する。
8. `orchestration` が Study2 候補を生成し、within -> across -> 実験A -> 実験D を順次実行する。
9. `report_builder` が `reports/*.csv` と `reports/run_manifest.json` を生成し、成果物キーを確定する。
10. 最終状態を `SUCCEEDED` または `FAILED` に遷移し、`GET /runs/{run_id}` で参照可能にする。

### 責務境界（APP/INF）
- APP は入力検証、状態遷移判定、データ正規化、成果物整形のロジックを担当する。
- INF は durable 実行基盤、Batch 実行管理、監視/IAM/配備制約を担当する。
- durable step 定義や運用パラメータの正本は [[DD-INF-DEP-001]] を参照し、本書はアプリ側の処理順と判定責務を正本とする。

## 受入条件
- RQ/BD から APP-DD へ辿れる reverse trace が成立している。
- INF-DD と APP-DD の責務重複がなく、参照境界が明確である。

## 変更履歴
- 2026-02-28: アプリ処理フロー（受付-列挙-投入-poll-正規化-集計）と APP/INF 責務境界を追記 [[DD-INF-DEP-001]]
- 2026-02-28: 初版作成（APP詳細の正本境界を定義） [[BD-SYS-ADR-001]]
