---
id: RQ-FR-017
title: run停止APIで進行中runを中断できる
doc_type: 機能要求
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-03-13
updated: '2026-03-13'
up:
  - '[[RQ-SC-001]]'
  - '[[RQ-UC-006]]'
related:
  - '[[RQ-FR-003]]'
  - '[[RQ-FR-015]]'
  - '[[RQ-RDR-004]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - FR
---

## SnowCard（日本語）
- 要求ID: RQ-FR-017
- 種別: 機能要求
- 優先度: MUST
- 要求: [[RQ-SH-001|管理者]]が `POST /runs/{run_id}/cancel` で非終端 [[RQ-GL-002|run]] の停止を要求できる。
- 要求（初期スコープ）: `QUEUED` または `RUNNING` の base run / repair run を対象とし、要求受理後は `CANCELLING`、停止完了後は `CANCELLED` として扱う。
- 根拠: 不要になった長時間実行や異常 run を早期停止し、不要コストと待機時間を抑制するため。
- 受入基準: 停止要求が受理されると新しい Batch submit が抑止され、最終的に `GET /runs/{run_id}` から `CANCELLED` が確認できる。
- 例外/エラー: 未知 `run_id` は Not Found、`SUCCEEDED/FAILED/PARTIAL` の終端 run は Conflict、`CANCELLING/CANCELLED` への再要求は冪等成功として扱う。
- 依存・関連: [[RQ-UC-006]]

## 変更履歴
- 2026-03-13: 初版作成（run 停止APIの要求を追加） [[RQ-RDR-004]]
