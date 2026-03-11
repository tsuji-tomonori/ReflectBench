---
id: RQ-RDR-003
title: invalid再処理APIとrepair run方式の追加
doc_type: 要求決定記録
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-11
updated: '2026-03-11'
up:
  - '[[RQ-DG-001]]'
related:
  - '[[RQ-UC-003]]'
  - '[[RQ-FR-012]]'
  - '[[RQ-FR-013]]'
  - '[[RQ-FR-015]]'
  - '[[RQ-FR-016]]'
  - '[[BD-SYS-ADR-002]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - RDR
---

## 決定
- `invalid/` に退避されたレコードの後処理は、元 [[RQ-GL-002|run]] の再実行ではなく、別APIで起動する repair run として扱う。
- repair run は親runを上書きせず、新しい `run_id` を採番して親子関係を追跡する。
- 初期スコープは `study1` の `invalid_only` に限定し、`renormalize` と `rerun` の2方式を許可する。
- repair run では `parent_run_id`、`repair_phase`、`repair_scope`、`repair_mode`、`rebuild_downstream` を必須追跡項目とする。
- `rebuild_downstream=true` の場合は、repair 後の Study1 正規化結果を基準に下流 phase と report を再構築する。

## 根拠
- `invalid/` は既存設計でも再処理入力として再利用する想定だが、現状は専用APIがなく運用手順が固定されていないため。
- 親runの成果物を後から上書きすると、`artifact_index`、status、運用監査の整合が崩れやすいため。
- parse failure の多くは成功済み shard の再実行なしで復旧できるため、全run再投入より修復コストが低いため。

## 影響
- 実験実行管理に `POST /runs/{run_id}/repairs` 相当の新規APIを追加する。
- `GET /runs/{run_id}` と `GET /runs/{run_id}/artifacts` から repair run の系譜と差分成果物を追跡できるようにする。
- Orchestrator に repair workflow、Study1 merge、下流再構築の分岐を追加する。
- 運用ランブックに「PARTIAL run から invalid のみを別runで復旧する」手順を追加する。

## 変更履歴
- 2026-03-11: 初版作成（invalid再処理APIとrepair run方式の要求決定を追加） [[RQ-RDR-003]]
