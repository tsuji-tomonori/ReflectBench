---
id: RQ-FR-015
title: invalid再処理APIでrepair runを起動できる
doc_type: 機能要求
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-11
updated: '2026-03-11'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-003]]'
related:
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-004]]'
  - '[[RQ-FR-012]]'
  - '[[RQ-FR-013]]'
  - '[[BD-SYS-ADR-002]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-015
- 種別: 機能要求
- 優先度: MUST
- 要求: [[RQ-SH-001|管理者]]が `POST /runs/{run_id}/repairs` で `invalid_only` repair run を起動できる。
- 要求（初期スコープ）: 初期リリースでは `phase=study1`、`mode=renormalize|rerun`、`models[]`、`record_ids[]`、`rebuild_downstream` を指定できる。
- 根拠: `PARTIAL` run の復旧で、成功済みレコードまで再実行しないため。
- 受入基準: 親runが終端状態かつ対象 invalid が存在する場合、repair run が新しい `run_id` で `QUEUED` として受理される。
- 例外/エラー: 親run未存在、親run未完了、対象 invalid 不在、未対応 phase/mode、重複リクエストは検証エラーで拒否する。
- 依存・関連: [[RQ-UC-003]]

## 変更履歴
- 2026-03-11: 初版作成（invalid再処理APIの起動要件を追加） [[RQ-RDR-003]]
