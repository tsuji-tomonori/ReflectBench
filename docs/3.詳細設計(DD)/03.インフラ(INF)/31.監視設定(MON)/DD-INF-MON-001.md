---
id: DD-INF-MON-001
title: run監視・通知詳細
doc_type: 監視詳細
phase: DD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
related:
  - '[[DD-INF-DEP-002]]'
  - '[[OPSREL-RUN-001]]'
  - '[[RQ-OBS-001-01]]'
  - '[[RQ-PS-001-01]]'
tags:
  - llm-temp-introspection
  - DD
  - MON
---

## 詳細仕様
- 可観測性は CloudWatch Metrics + Logs + Alarm を正本とし、必要時のみ SNS 通知を有効化する。
- `run_id` をログ相関キーとし、Lambdaログとメトリクスを同一単位で追跡可能にする。

## メトリクス定義
| メトリクス | 単位 | 集計軸 | 説明 |
|---|---|---|---|
| `RunStarted` | Count | `run_id` | [[RQ-GL-002|run]] 開始件数 |
| `RunSucceeded` | Count | `run_id` | [[RQ-GL-002|run]] 成功件数 |
| `RunFailed` | Count | `run_id` | [[RQ-GL-002|run]] 失敗件数 |
| `RunDurationSec` | Seconds | `run_id` | [[RQ-GL-002|run]] 所要時間 |
| `ShardRetryCount` | Count | `phase,model` | [[RQ-GL-004|shard]] retry 件数 |
| `ParseFailureCount` | Count | `phase,model` | parse failure 件数 |
| `BatchFailureRate` | Percent | `phase` | Batch job 失敗率 |

## アラーム定義
| アラーム | 条件 | 重大度 | 初動 |
|---|---|---|---|
| `OrchestratorFailure` | `RunFailed >= 1` | High | failure step を特定 |
| `RunDurationSLOViolation` | `RunDurationSec > 86400` | High | ボトルネック [[RQ-GL-003|phase]] を切り分け |
| `BatchFailureRateHigh` | `BatchFailureRate > 2%` | Medium | [[RQ-GL-004|shard]] 再試行と入力破損確認 |
| `ParseFailureRateHigh` | `ParseFailureCount / total > 5%` | Medium | prompt / parser / schema を確認 |

## 通知方針
- SNS有効時は `run_id`, `phase`, `state`, `last_error.step`, `last_error.reason` を通知payloadに含める。
- 失敗通知はアラーム発砲時、完了通知は `RunSucceeded` 送信時のみ発行する。

## 運用確認
- 日次: 前日完了 [[RQ-GL-002|run]] の `RunDurationSec` を確認する。
- 週次: `run_manifest.json` の retry/invalid 件数を集計し、しきい値超過を確認する。
- 月次: model別失敗率の偏りを確認し、[[RQ-GL-004|shard]]_size/poll_interval の見直し候補を記録する。

## 受入条件
- [[RQ-GL-002|run]] 開始/完了/失敗、retry件数、parse failure件数が CloudWatch で可視化される。
- 24時間超過 [[RQ-GL-002|run]] をアラームで検知できる。
- 障害時に `run_id` 単位でログ追跡できる。

## 変更履歴
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]監視メトリクスとアラーム基準を定義） [[BD-SYS-ADR-001]]
