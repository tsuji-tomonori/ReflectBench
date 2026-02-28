---
id: BD-SYS-ADR-001
title: 単一リージョン Bedrock Batch + Durable Orchestrator 採用
doc_type: アーキテクチャ決定記録
phase: BD
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[BD-INF-DEP-001]]'
related:
  - '[[RQ-PP-001]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
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
tags:
  - llm-temp-introspection
  - BD
  - ADR
---

## 決定
- 実行リージョンは `ap-southeast-2` に固定する。
- 推論実行は Bedrock Batch Inference を唯一の経路とする。
- 長時間制御は Lambda Durable Functions を有効化した `orchestrator_fn` で実施する。

## 根拠
- 採用モデル（Nova Micro/Gemma/Ministral/Qwen3 32B）を単一リージョンで整合させられる。
- 73,200 コール規模の [[RQ-GL-002|run]] で同期API中心実行は運用負荷が高く、Batch + durable が最も単純。

## トレードオフ
- 低遅延な逐次実行より、バッチ待機時間を受け入れる。
- strict JSON + parser 検証により、プロンプト設計の制約が増える。

## 影響
- `start_run_fn` / `orchestrator_fn` / `status_fn` の3 Lambda 構成を前提とする。
- 失敗時は [[RQ-GL-004|shard]] 単位 retry と `invalid/` 退避の二段回復を標準とする。

## 変更履歴
- 2026-02-28: DD-INF/DD-APP の詳細分割に合わせ関連リンクを拡張 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（デプロイ実行方式の基幹決定を記録） [[BD-SYS-ADR-001]]
