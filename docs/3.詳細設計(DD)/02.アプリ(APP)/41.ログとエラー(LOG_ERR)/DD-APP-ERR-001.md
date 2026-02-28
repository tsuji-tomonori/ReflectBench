---
id: DD-APP-ERR-001
title: ログ・エラー処理詳細
doc_type: エラー詳細
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-INF-MON-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
  - '[[RQ-OBS-001-01]]'
  - '[[RQ-SEC-001-01]]'
tags:
  - llm-temp-introspection
  - DD
  - APP
  - ERR
---

## 詳細仕様
- すべての処理ログは `run_id`, `phase`, `step`, `trace_id` を共通キーとして出力する。
- エラーは `validation`, `dependency`, `timeout`, `internal` に分類し、`retryable` を必須判定値にする。

## エラーモデル
| フィールド | 型 | 説明 |
|---|---|---|
| `code` | string | 機械判定用コード |
| `message` | string | 運用向け要約 |
| `category` | string | `validation/dependency/timeout/internal` |
| `retryable` | boolean | 再試行可否 |
| `step` | string | 失敗step |
| `trace_id` | string | ログ相関ID |

## ログ出力規約
- INFO: step 開始/完了、件数、時間。
- WARN: `invalid/` 退避、部分失敗継続。
- ERROR: step 停止、再試行不能、最終失敗。
- 秘密情報（トークン、認証情報、全文prompt）はログ出力しない。

## 失敗時動作
- `validation`: `400` または `invalid/` へ退避して継続。
- `dependency`: backoff 再試行後、上限到達で `FAILED`。
- `timeout`: step を中断し `last_error` を更新。
- `internal`: 即時失敗とし調査用コンテキストを記録。

## 受入条件
- `run_id` 単位でエラー追跡と原因分類が可能である。
- 可観測性メトリクスとエラー分類が矛盾しない。

## 変更履歴
- 2026-02-28: 初版作成（ログ相関キーとエラー分類規約を定義） [[BD-SYS-ADR-001]]
