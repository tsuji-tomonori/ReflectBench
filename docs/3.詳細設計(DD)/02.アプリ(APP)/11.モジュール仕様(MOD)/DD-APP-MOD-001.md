---
id: DD-APP-MOD-001
title: 実験実行モジュール仕様
doc_type: モジュール仕様
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
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
tags:
  - llm-temp-introspection
  - DD
  - APP
  - MOD
---

## 詳細仕様
- モジュールは `run_api`, `orchestration`, `batch_adapter`, `normalizer`, `report_builder` に分割する。
- 各モジュールは pure logic を優先し、AWS 依存は adapter 境界に隔離する。

## モジュール責務
| モジュール | 主な責務 | 入力 | 出力 |
|---|---|---|---|
| `run_api` | `POST/GET` ハンドラ処理 | HTTP request | API response |
| `orchestration` | step 遷移と進捗更新 | `RunConfig` | `RunStatus` |
| `batch_adapter` | Bedrock job 投入/取得 | [[RQ-GL-005|manifest]] key | job status |
| `normalizer` | strict JSON 検証と schema 変換 | batch output | normalized/invalid |
| `report_builder` | CSV / `run_manifest.json` 生成 | normalized records | reports keys |

## 処理順序
1. `run_api` が入力検証を実施し、`idempotency_key` が既存一致なら既存 `run_id` を返す。
2. 新規受付時のみ `run_id` 発行と `RunConfig` 保存を行い、`orchestration` 起動を要求する。
3. `orchestration` が Study1 列挙 -> Batch submit -> Job poll を進行し、都度 `batch_adapter` を呼び出す。
4. `normalizer` が出力を検証し、失敗レコードを `invalid/` へ分離する。
5. `orchestration` が Study2 within/across、実験A、実験D を順次進行する。
6. `report_builder` が成果物を確定し、`RunStatus` を `SUCCEEDED/FAILED` へ遷移する。

## 受入条件
- モジュール単位で単体テスト可能な責務分離になっている。
- retry 時に `orchestration` が同一 `record_id` で再処理できる。

## 変更履歴
- 2026-02-28: 総論のアプリ処理フローに合わせて処理順序を具体化（idempotency/retry/終状態遷移を明確化） [[DD-APP-OVR-001]]
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]実行ロジックのモジュール分割を定義） [[BD-SYS-ADR-001]]
