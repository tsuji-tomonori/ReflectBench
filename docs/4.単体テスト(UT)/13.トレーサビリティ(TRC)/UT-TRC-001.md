---
id: UT-TRC-001
title: UTケース・ペアワイズ対応マトリクス
doc_type: 単体テストトレーサビリティ
phase: UT
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-11'
up:
  - '[[UT-PLAN-001]]'
related:
  - '[[RQ-FR-001]]'
  - '[[RQ-FR-014]]'
  - '[[RQ-PS-001-01]]'
  - '[[RQ-OBS-001-01]]'
  - '[[RQ-SEC-001-01]]'
  - '[[UT-CASE-BE-001]]'
  - '[[UT-CASE-BE-002]]'
  - '[[UT-CASE-BE-003]]'
  - '[[UT-CASE-BE-004]]'
  - '[[UT-CASE-BE-005]]'
  - '[[UT-CASE-BE-006]]'
  - '[[UT-CASE-BE-007]]'
  - '[[UT-CASE-APP-001]]'
  - '[[UT-CASE-APP-002]]'
  - '[[UT-CASE-APP-003]]'
  - '[[UT-CASE-APP-004]]'
  - '[[UT-CASE-APP-005]]'
  - '[[UT-CASE-APP-006]]'
  - '[[UT-CASE-APP-007]]'
  - '[[UT-CASE-APP-008]]'
  - '[[UT-CASE-APP-009]]'
  - '[[UT-PW-001]]'
  - '[[UT-PW-BE-API-001]]'
  - '[[UT-PW-APP-ORCH-001]]'
  - '[[UT-PW-APP-DATA-001]]'
  - '[[UT-PW-APP-ERR-001]]'
  - '[[UT-PW-APP-MON-001]]'
tags:
  - llm-temp-introspection
  - UT
  - TRC
---

## 目的
- UT-CASE と UT-PW の対応関係を一元化し、要求からテスト設計までの追跡性を可視化する。

## 要求 -> UTケース対応
| 要求 | 観点 | UT-CASE |
|---|---|---|
| [[RQ-FR-001]] | [[RQ-GL-002|run]] 起動/API受理 | [[UT-CASE-BE-001]], [[UT-CASE-BE-002]], [[UT-CASE-BE-003]] |
| [[RQ-FR-003]] | status API | [[UT-CASE-BE-004]], [[UT-CASE-BE-005]] |
| [[RQ-FR-004]] | artifacts API | [[UT-CASE-BE-006]] |
| [[RQ-FR-005]] | Study1 列挙 | [[UT-CASE-APP-001]] |
| [[RQ-FR-006]] | Batch 投入 | [[UT-CASE-APP-001]], [[UT-CASE-APP-003]], [[UT-CASE-APP-010]] |
| [[RQ-FR-007]] | durable 待機 | [[UT-CASE-APP-001]], [[UT-CASE-APP-002]] |
| [[RQ-FR-008]] | within/across 分離 | [[UT-CASE-APP-001]] |
| [[RQ-FR-009]] | 実験A 2段実行 | [[UT-CASE-APP-001]] |
| [[RQ-FR-010]] | 実験D 2条件 | [[UT-CASE-APP-001]] |
| [[RQ-FR-011]] | strict JSON + schema | [[UT-CASE-APP-004]], [[UT-CASE-APP-005]] |
| [[RQ-FR-012]] | [[RQ-GL-004|shard]] 単位再試行 | [[UT-CASE-APP-003]], [[UT-CASE-APP-002]] |
| [[RQ-FR-013]] | deterministic ID | [[UT-CASE-APP-006]] |
| [[RQ-FR-014]] | 成果物6種出力 | [[UT-CASE-APP-007]], [[UT-CASE-BE-006]] |
| [[RQ-FR-015]] | repair API 起動 | [[UT-CASE-BE-007]] |
| [[RQ-FR-016]] | repair 系譜/差分追跡 | [[UT-CASE-BE-004]], [[UT-CASE-BE-006]], [[UT-CASE-BE-007]] |
| [[RQ-PS-001-01]] | 24h 完了観点 | [[UT-CASE-APP-001]], [[UT-CASE-APP-008]] |
| [[RQ-OBS-001-01]] | [[RQ-GL-002|run]] メトリクス可視化 | [[UT-CASE-APP-008]], [[UT-CASE-APP-009]] |
| [[RQ-SEC-001-01]] | エラー情報統制 | [[UT-CASE-APP-009]], [[UT-CASE-BE-005]] |

## UT-CASE -> ペアワイズ対応
| UT-CASE | 主な組合せ観点 | UT-PW |
|---|---|---|
| [[UT-CASE-BE-001]] | API入力因子 | [[UT-PW-BE-API-001]] |
| [[UT-CASE-BE-002]] | API入力境界 | [[UT-PW-BE-API-001]] |
| [[UT-CASE-BE-003]] | 冪等キー条件 | [[UT-PW-BE-API-001]] |
| [[UT-CASE-BE-007]] | repair API 入力条件 | [[UT-PW-BE-API-001]] |
| [[UT-CASE-APP-001]] | step遷移 | [[UT-PW-APP-ORCH-001]] |
| [[UT-CASE-APP-002]] | 部分失敗継続 | [[UT-PW-APP-ORCH-001]] |
| [[UT-CASE-APP-003]] | retry制御 | [[UT-PW-APP-ORCH-001]] |
| [[UT-CASE-APP-004]] | 正常データ | [[UT-PW-APP-DATA-001]] |
| [[UT-CASE-APP-005]] | 異常データ | [[UT-PW-APP-DATA-001]] |
| [[UT-CASE-APP-006]] | ID入力欠落 | [[UT-PW-APP-DATA-001]] |
| [[UT-CASE-APP-008]] | 監視送信条件 | [[UT-PW-APP-MON-001]] |
| [[UT-CASE-APP-009]] | エラー分類 | [[UT-PW-APP-ERR-001]] |
| [[UT-CASE-APP-010]] | Batch shard 境界 | [[UT-PW-APP-ORCH-001]] |

## カバレッジ確認観点
- すべての `RQ-FR-001..016` が少なくとも1つ以上の UT-CASE に対応している。
- 3因子以上の分岐を持つ主要観点（API入力、orchestration、data、error、monitoring）が UT-PW で補完されている。

## 変更履歴
- 2026-03-12: Bedrock Batch shard 境界の UT 追跡を追加し、FR 範囲表記を更新 [[DD-INF-DEP-002]]
- 2026-03-11: repair API と lineage/repair 応答の追跡関係を追加 [[RQ-RDR-003]]
- 2026-02-28: 初版作成（UT-CASE と UT-PW の対応マトリクスを追加） [[RQ-RDR-002]]
