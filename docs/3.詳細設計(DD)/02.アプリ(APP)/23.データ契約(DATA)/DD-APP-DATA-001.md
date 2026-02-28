---
id: DD-APP-DATA-001
title: アプリデータモデル詳細
doc_type: データ契約
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[RQ-FR-011]]'
  - '[[RQ-FR-013]]'
  - '[[RQ-FR-014]]'
tags:
  - llm-temp-introspection
  - DD
  - APP
  - DATA
---

## 詳細仕様
- [[RQ-GL-012|canonical schema]] は [[DD-INF-DATA-001]] を正本とし、本書はアプリ側クラス定義と変換責務を定義する。
- strict JSON の decode 後に Pydantic モデルへ変換し、型不一致は例外化して `invalid/` へ送る。

## アプリモデル
| モデル | 用途 | 主なフィールド |
|---|---|---|
| `RunCreateRequest` | API入力 | loops, full_cross, [[RQ-GL-004|shard]]_size, poll_interval_sec |
| `RunCreateResponse` | API出力 | [[RQ-GL-002|run]]_id, accepted_at, initial_[[RQ-GL-003|phase]], state |
| `RunStatusView` | 状態応答 | [[RQ-GL-003|phase]], state, progress, retry_count, last_error |
| `ManifestLine` | Batch入力行 | record_id, prompt_payload, output_key |
| `InvalidRecord` | 検証失敗保存 | record_id, [[RQ-GL-003|phase]], reason, raw_text |

## 変換ルール
- `RunStatus` -> `RunStatusView` 変換で `datetime` は ISO8601(UTC) へ統一する。
- `PredictionRecord` の `predicted_label` は語彙正規化後に保存する。
- `record_id` は生成関数を単一化し、呼び出し側で直接生成しない。

## I/O責務
- 入力: batch output JSON、[[RQ-GL-002|run]]設定JSON、status中間データ。
- 出力: normalized JSONL、invalid JSONL、report 用 CSV レコード。

## 受入条件
- Pydantic モデルで schema 不整合を検出できる。
- 同一条件では常に同一 `record_id` を生成する。

## 変更履歴
- 2026-02-28: 初版作成（アプリ側データモデルと変換責務を定義） [[BD-SYS-ADR-001]]
