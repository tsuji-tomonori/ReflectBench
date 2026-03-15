---
id: RQ-PP-001
title: llm-temp-introspection の目的
doc_type: プロジェクトの目的
phase: RQ
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-13'
up: []
related:
  - '[[RQ-RDR-001]]'
  - '[[RQ-RDR-002]]'
  - '[[RQ-RDR-004]]'
  - '[[RQ-SC-001]]'
  - '[[RQ-PC-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-017]]'
  - '[[RQ-AV-001-01]]'
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-INF-OVR-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-OVR-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[OPSREL-RUN-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - PP
---

## 目的
- LLM の温度内省に関する Study1 / Study2 / 追加実験 A / D を、単一リージョンのフルサーバレス構成で再現可能に運用する。
- 実験実行と成果物生成を Bedrock Batch Inference 中心へ統一し、長時間処理を Lambda Durable Functions で安定運用できる状態にする。

## 成果物
- 実行管理 API（`POST /runs`, `POST /runs/{run_id}/cancel`, `POST /runs/{run_id}/repairs`, `GET /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/artifacts`）。
- 実験成果物（`runs/{run_id}/...` 配下の [[RQ-GL-005|manifest]] / batch-output / normalized / reports）。
- レポート成果物（`study1_summary.csv`, `study2_within.csv`, `study2_across.csv`, `experiment_a.csv`, `experiment_d.csv`, `run_manifest.json`）。

## 成功条件
- Study1 10 ループ、Study2 within/across 完全クロス、追加実験 A / D を同一 [[RQ-GL-002|run]] で完走できる。
- 不要または異常な [[RQ-GL-002|run]] を停止要求し、`CANCELLED` まで到達できる。
- 採用モデル（Nova Micro, Gemma 3 12B IT, Ministral 3 8B, Qwen3 32B）を `ap-southeast-2` で一貫して呼び出せる。
- 実行中断や JSON 解析失敗が発生しても、[[RQ-GL-004|shard]] 単位で再試行または `invalid/` 退避により復旧できる。

## 前提
- リージョンは `ap-southeast-2` 固定。
- `Qwen3 32B` は `qwen.qwen3-32b-v1:0` を使用。
- 追加実験 A の editor は `apac.amazon.nova-micro-v1:0` 固定。
- すべての LLM 実行は Bedrock Batch Inference を使用。
- 環境は1環境のみで、常時開放は前提としない。
- 利用者は[[RQ-SH-001|管理者]]のみとし、冗長化は採用しない。

## 正本分担ルール
- インフラ/全体構成の正本は `plan.md` とし、BD/INF/DD-INF 文書群へ反映する。
- 実験条件/閾値/分析手順の正本は `.ai_workspace/llm-temp-introspection` とし、RQ-FR/DD-APP 文書群へ反映する。
- 両者が競合する場合は「基盤運用プロファイル（plan）」と「実験詳細プロファイル（.ai_workspace）」を分離して記述する。

## 変更履歴
- 2026-03-13: cancel API を成果物/成功条件へ追加 [[RQ-RDR-004]]
- 2026-02-28: 正本分担ルール（infra=plan, experiment=.ai_workspace）を追加 [[RQ-RDR-002]]
- 2026-02-28: DD-INF/DD-APP への逆リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: プロジェクト制約（単一環境/管理者単独/非冗長）を前提へ追記 [[RQ-RDR-002]]
- 2026-02-28: SC/FR/NFR への関連リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成（plan.md の実装前提と POC の運用知見を統合） [[RQ-RDR-001]]
