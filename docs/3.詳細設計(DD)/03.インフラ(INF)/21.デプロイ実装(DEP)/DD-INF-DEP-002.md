---
id: DD-INF-DEP-002
title: デプロイ詳細（実行パラメータと運用制約）
doc_type: デプロイ詳細
phase: DD
version: 1.0.3
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
related:
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-OVR-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-INF-IAM-001]]'
  - '[[DD-INF-MON-001]]'
  - '[[DD-INF-PIPE-001]]'
  - '[[DD-APP-OVR-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-ERR-001]]'
  - '[[RQ-PC-001]]'
  - '[[RQ-COST-001-01]]'
  - '[[RQ-COST-001-02]]'
  - '[[BD-SYS-ADR-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - DD
  - DEP
---

## 実行パラメータ（初期値）
| 項目 | 値 | 理由 |
|---|---|---|
| region | `ap-southeast-2` | 採用モデルを単一リージョンで閉じるため |
| [[RQ-GL-004|shard]] size | `500` | Batch 最小100件を満たし運用しやすいため |
| poll interval | `180 sec` | 待機オーバーヘッドと追従性のバランス |
| durable timeout | `7 days` | 長時間 [[RQ-GL-002|run]] を分割せず完走するため |
| durable retention | `30 days` | 再調査と再実行判断に必要な保持期間 |
| editor model | `apac.amazon.nova-micro-v1:0` | 追加実験Aの固定前提 |

## 運用制約
- 単一環境のみで運用し、環境分割を行わない。
- 常時開放は行わず、必要時のみ起動して実験を実施する。
- 冗長化構成は採用せず、障害時は再試行と再実行で復旧する。

## コスト見積もり（`plan.md` ベース）

### 1 run あたりのモデル費（Bedrock Batch, `ap-southeast-2`）
| モデル | Bedrock model ID | Batch単価（Input / Output, per 1M tokens） | 推定 Input | 推定 Output | 推定費用/ run |
|---|---|---:|---:|---:|---:|
| Nova Micro | `apac.amazon.nova-micro-v1:0` | $0.0175 / $0.0700 | 3.87M | 3.40M | $0.31 |
| Gemma 3 12B IT | `google.gemma-3-12b-it` | $0.04635 / $0.14935 | 3.51M | 3.07M | $0.62 |
| Ministral 3 8B | `mistral.ministral-3-8b-instruct` | $0.07725 / $0.07725 | 3.51M | 3.07M | $0.51 |
| Qwen3 32B | `qwen.qwen3-32b-v1:0` | $0.0773 / $0.3090 | 3.51M | 3.07M | $1.22 |

- 合計: **$2.66 / run**（`plan.md` の試算値を採用）
- 比較: 同条件オンデマンド概算 **$5.31 / run**
- 誤差前提: prompt/response 長の proxy 試算のため、請求実績は概ね **±20-30%** を許容する。

### phase 別モデル費（1 run 概算）
| phase | 概算費用 |
|---|---:|
| Study1 | $0.26 |
| Study2 within | $0.14 |
| Study2 across | $0.42 |
| 追加実験A: edit | $0.03 |
| 追加実験A: predict | $0.56 |
| 追加実験D: blind | $0.70 |
| 追加実験D: wrong-label | $0.56 |

- 支配要因は Qwen3 32B の output 単価であり、追加実験Dで費用寄与が最大になる。
- 受入基準 `[[RQ-COST-001-01]]` に対し、現行試算は **$2.66 / run < $3.50 / run** を満たす。

### サーバレス基盤費（アイドル時の考え方）
- 時間課金の常時起動リソース（EC2/RDS/NAT Gateway/EKS node）は採用しない。
- 従量課金対象は API Gateway / Lambda / S3 / CloudWatch Logs / DynamoDB（PAY_PER_REQUEST）とする。
- この規模ではモデル費が支配的であり、基盤費は副次的とする（詳細は `[[RQ-COST-001-01]]` の週次試算で監視）。

## 正本参照
- API応答構造の正本は [[DD-INF-API-001]] とする。
- [[RQ-GL-005|manifest]]/[[RQ-GL-012|canonical schema]]/成果物キー契約の正本は [[DD-INF-DATA-001]] とする。
- 監視指標・アラームは [[DD-INF-MON-001]]、最小権限は [[DD-INF-IAM-001]]、配備チェーンは [[DD-INF-PIPE-001]] を参照する。
- 実験条件・閾値・分析物の詳細は DD-APP 群（[[DD-APP-OVR-001]], [[DD-APP-MOD-001]], [[DD-APP-DATA-001]]）を正本とする。

## 状態管理方針
- `RunStatus` と `idempotency_key` は DynamoDB（`run_control_table`）で管理する。
- 成果物本文は S3 を正本とし、DynamoDB にはキー参照（`artifacts_index`）のみ保持する。
- 状態更新は「S3 書き込み成功後に DynamoDB 更新」を基本順序とする。

## モデルルーティング
- `NOVA_MICRO` -> `apac.amazon.nova-micro-v1:0`
- `GEMMA_3_12B_IT` -> `google.gemma-3-12b-it`
- `MINISTRAL_3_8B` -> `mistral.ministral-3-8b-instruct`
- `QWEN3_32B` -> `qwen.qwen3-32b-v1:0`

## [[RQ-GL-005|manifest]] 仕様
- 入力形式は JSONL（1 line = 1 推論要求）。
- 保存先は `runs/{run_id}/manifests/{phase}/{model}/part-xxxxx.jsonl`。
- 各 line には source 条件、record_id、出力先キーを埋め込む。

## 正規化仕様
- モデル出力は strict JSON のみ許可する。
- Pydantic 検証失敗は `runs/{run_id}/invalid/{phase}/{model}/...` へ保存する。
- `invalid/` は再処理キュー入力として再利用できる形式にする。

## 監視・通知
- CloudWatch メトリクス:
  - [[RQ-GL-002|run]] 開始/完了/失敗件数
  - [[RQ-GL-004|shard]] submit 数、retry 数
  - parse failure 数
- Alarm:
  - Orchestrator failure
  - Batch job failure rate 上昇
  - parse failure rate 閾値超過
- SNS（任意）:
  - [[RQ-GL-002|run]] 完了通知
  - [[RQ-GL-002|run]] 失敗通知

## API 応答設計（抜粋）
- `GET /runs/{run_id}` は `phase`, `state`, `progress`, `last_error` を返す。
- `GET /runs/{run_id}/artifacts` は `reports`, `normalized`, `invalid` のキー一覧を返す。

## 再試行方針
- Bedrock 側失敗: [[RQ-GL-004|shard]] 単位で 1 回再試行。
- Lambda 一時失敗: exponential backoff で step 再実行。
- 部分失敗許容: `invalid/` を除外して集計継続し、`run_manifest.json` に除外件数を明記。

## 受入確認
- 1 [[RQ-GL-002|run]] あたりの LLM call 総数（73,200）と [[RQ-GL-003|phase]] 別件数が [[RQ-GL-002|run]] [[RQ-GL-005|manifest]] で追跡できる。
- 追加実験 D（[[RQ-GL-010|blind]] / [[RQ-GL-011|wrong-label]]）の成果物が [[RQ-GL-003|phase]] 別に分離される。
- 集計 CSV と source [[RQ-GL-002|run]] の関連が `record_id` で逆引きできる。

## 変更履歴
- 2026-02-28: `plan.md` ベースのモデル費見積もりと phase 別費用を追加し、RQ-COST トレースを追記 [[RQ-RDR-002]]
- 2026-02-28: 実験詳細の正本参照先を DD-APP 群へ追加 [[RQ-RDR-002]]
- 2026-02-28: API/データ/IAM/監視/CI_CDの正本分離を追記 [[BD-SYS-ADR-001]]
- 2026-02-28: 制約（単一環境/非常時運用/非冗長）を運用パラメータへ反映 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（plan.md の推奨初期値・retry方針・監視観点を定義） [[BD-SYS-ADR-001]]
