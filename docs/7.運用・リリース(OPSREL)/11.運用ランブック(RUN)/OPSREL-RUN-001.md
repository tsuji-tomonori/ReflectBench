---
id: OPSREL-RUN-001
title: Bedrock Batch 実験運用ランブック
doc_type: 運用ランブック
phase: AT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
related:
  - '[[RQ-PP-001]]'
  - '[[RQ-PC-001]]'
  - '[[RQ-UC-003]]'
  - '[[RQ-OBS-001-02]]'
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
  - '[[BD-SYS-ADR-001]]'
tags:
  - llm-temp-introspection
  - OPSREL
  - RUN
---

## 目的
- Study1 / Study2 / 追加実験 A / D のフル [[RQ-GL-002|run]] を、失敗時の再試行を含めて運用可能にする。

## 必要時運用
1. `POST /runs` で [[RQ-GL-002|run]] を開始する。
2. `GET /runs/{run_id}` で [[RQ-GL-003|phase]] と進捗を監視する。
3. 完了後 `GET /runs/{run_id}/artifacts` で reports を取得する。
4. 実験終了後は常時開放を維持せず、不要な待機実行を停止する。

## 実行開始時の確認
- リージョンが `ap-southeast-2` であること。
- editor が `apac.amazon.nova-micro-v1:0` に固定されていること。
- [[RQ-GL-004|shard]] size が 500、poll interval が 180 秒であること。
- output 先 S3 prefix に書き込み権限があること。

## 完了判定
- `reports/run_manifest.json` が存在する。
- `study1_summary.csv`, `study2_within.csv`, `study2_across.csv`, `experiment_a.csv`, `experiment_d.csv` が存在する。
- `RunStatus.state` が `SUCCEEDED` である。

## 失敗時対応
### Batch job failure
1. 失敗 [[RQ-GL-004|shard]] を特定する。
2. [[RQ-GL-004|shard]] 単位で 1 回再試行する。
3. 再失敗時は [[RQ-GL-002|run]] を `FAILED` にし、原因を `last_error` へ保存する。

### JSON parse failure
1. 失敗レコードを `invalid/` に退避する。
2. invalid 件数を [[RQ-GL-002|run]] [[RQ-GL-005|manifest]] へ記録する。
3. 後続集計は invalid を除外して継続する。

### Orchestrator failure
1. CloudWatch Logs で failure step を特定する。
2. 入力破損か依存障害かを切り分ける。
3. 再開可能な step から再実行する。

## コスト監視
- 1 [[RQ-GL-002|run]] の目安は Bedrock モデル費 `$2.66`。
- 連続実行時は週次で `run_manifest.json` を集計し、[[RQ-GL-003|phase]] 別コスト比率を確認する。
- Qwen3 32B の output 単価が支配的なため、追加実験 D の件数増加を最優先監視対象にする。

## 変更履歴
- 2026-02-28: 非常時運用（常時開放しない）制約を反映 [[BD-SYS-ADR-001]]
- 2026-02-28: UC/NFR（可観測性）への追跡リンクを追加 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（plan.md の運用初期値と障害対応を Runbook 化） [[BD-SYS-ADR-001]]
