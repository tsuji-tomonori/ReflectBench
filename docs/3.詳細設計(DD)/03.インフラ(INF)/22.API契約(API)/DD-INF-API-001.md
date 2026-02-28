---
id: DD-INF-API-001
title: run制御API詳細
doc_type: API詳細
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-004]]'
tags:
  - llm-temp-introspection
  - DD
  - API
---

## 詳細仕様
- 対象APIは `POST /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/artifacts` の3本とする。
- 外部契約キーは `snake_case` を正本とし、内部実装の命名差は変換層で吸収する。

## エンドポイント一覧
| メソッド | パス | 役割 | 正常応答 |
|---|---|---|---|
| `POST` | `/runs` | [[RQ-GL-002|run]] 作成と durable 起動 | `202 Accepted` |
| `GET` | `/runs/{run_id}` | [[RQ-GL-002|run]] 状態取得 | `200 OK` |
| `GET` | `/runs/{run_id}/artifacts` | 成果物キー一覧取得 | `200 OK` |

## `POST /runs`
### request body
| キー | 型 | 必須 | 初期値/制約 |
|---|---|---|---|
| `loops` | integer | Yes | `10` 固定 |
| `full_cross` | boolean | Yes | `true` 固定 |
| `shard_size` | integer | No | `500`（100以上） |
| `poll_interval_sec` | integer | No | `180` |
| `editor_model` | string | No | `apac.amazon.nova-micro-v1:0` |
| `idempotency_key` | string | No | 同値再送時に同一 `run_id` を返す |

### response body (`202`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `accepted_at` | string(datetime) | 受付時刻（UTC ISO8601） |
| `initial_phase` | string | `STUDY1_ENUMERATE` |
| `state` | string | `QUEUED` |

## `GET /runs/{run_id}`
### response body (`200`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `phase` | string | 現在フェーズ |
| `state` | string | `QUEUED/RUNNING/SUCCEEDED/FAILED/PARTIAL` |
| `progress` | object | `completed_steps`, `total_steps`, `percent` |
| `retry_count` | integer | 累積 retry 回数 |
| `last_error` | object\|null | 直近エラー（`step`,`reason`,`retryable`） |
| `started_at` | string(datetime)\|null | 実行開始時刻 |
| `finished_at` | string(datetime)\|null | 実行完了時刻 |

## `GET /runs/{run_id}/artifacts`
### response body (`200`)
| キー | 型 | 内容 |
|---|---|---|
| `run_id` | string | 実行ID |
| `reports` | string[] | CSV/[[RQ-GL-005|manifest]]キー一覧 |
| `normalized` | string[] | 正規化データキー一覧 |
| `invalid` | string[] | 検証失敗データキー一覧 |

## エラー契約
- `400 Bad Request`: 入力不正（必須不足、制約違反）
- `404 Not Found`: 未知 `run_id`
- `409 Conflict`: 重複起動拒否（同一 `idempotency_key` が異条件）
- `500 Internal Server Error`: durable 起動失敗や状態取得失敗

## 状態遷移
`QUEUED -> RUNNING -> SUCCEEDED|FAILED|PARTIAL`

- `PARTIAL` は主要レポート出力済みかつ `invalid/` 除外継続で完走した状態を示す。

## 受入条件
- `POST /runs` が `202` と `run_id` を返し、`config.json` 保存済みである。
- `GET /runs/{run_id}` で [[RQ-GL-003|phase]]/state/progress/last_error が取得できる。
- `GET /runs/{run_id}/artifacts` に 5 CSV + `run_manifest.json` が含まれる。

## 変更履歴
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]制御APIの入出力契約を定義） [[BD-SYS-ADR-001]]
