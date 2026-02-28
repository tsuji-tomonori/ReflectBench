---
id: RQ-SC-001
title: llm-temp-introspection スコープ定義
doc_type: プロジェクトのスコープ
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-PP-001]]'
related:
  - '[[RQ-GL-001]]'
  - '[[RQ-PC-001]]'
  - '[[RQ-SH-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-014]]'
tags:
  - llm-temp-introspection
  - RQ
  - SC
---

## 目的
- 実験運用対象を Study1 / Study2 / 追加実験A / 追加実験D に限定し、要求境界を固定する。

## 対象（In Scope）
- 実行API（`POST /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/artifacts`）
- Bedrock Batch Inference による推論実行
- Lambda Durable Functions による長時間 orchestration
- S3 成果物保存（[[RQ-GL-005|manifest]], batch-output, normalized, reports）
- レポートCSV出力と [[RQ-GL-002|run]] [[RQ-GL-005|manifest]] 出力
- 単一環境での実験運用（利用者は[[RQ-SH-001|管理者]]のみ）

## 正本参照境界
- インフラ/全体像（リージョン、基盤構成、運用制約）の正本は `plan.md` とする。
- 実験詳細（Study 条件、閾値、分析手順、可視化成果物）の正本は `.ai_workspace/llm-temp-introspection` とする。
- 設計書には両者を併記せず、該当領域の正本へリンクして整合を維持する。

## 非対象（Out of Scope）
- リアルタイム推論API（同期推論）
- UIアプリケーションの新規開発
- `docs/2.基本設計(BD)/03.アプリ(APP)` 配下の旧UI/運用API文書群の新規拡張（当面は参考情報として扱い、正本要件として採用しない）
- 学習・ファインチューニング機能
- モデルプロバイダをまたぐ自動価格最適化
- 常時開放を前提とした24時間運用
- 複数環境運用（dev/stg/prod 分離）
- 冗長化構成（多重系、Multi-AZ前提構成）

## 完了条件（Definition of Done）
- Study1 / Study2(within+across) / A / D が1 [[RQ-GL-002|run]]で完走できる。
- 失敗時に [[RQ-GL-004|shard]] 単位再試行または `invalid/` 退避で復旧できる。
- 成果物6種（5 CSV + [[RQ-GL-002|run]]_[[RQ-GL-005|manifest]]）が必ず出力される。
- コスト最小化方針（[[RQ-PC-001]]）に反しない構成で運用できる。

## 変更履歴
- 2026-02-28: 正本参照境界（plan /.ai_workspace）を追加 [[RQ-RDR-002]]
- 2026-02-28: BD-APP旧文書群を非対象へ明示し、現行スコープ（実験運用API中心）との衝突を解消 [[RQ-RDR-002]]
- 2026-02-28: 制約（単一環境/非常時運用/非冗長/管理者のみ）をスコープへ反映 [[RQ-RDR-002]]
- 2026-02-28: 初版作成（今回スコープを定義） [[RQ-RDR-002]]
