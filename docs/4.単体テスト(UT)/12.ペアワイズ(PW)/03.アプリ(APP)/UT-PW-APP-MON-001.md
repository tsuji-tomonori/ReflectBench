---
id: UT-PW-APP-MON-001
title: 監視送信条件ペアワイズ
doc_type: ペアワイズ設計
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PW-001]]'
related:
  - '[[UT-CASE-APP-008]]'
  - '[[DD-INF-MON-001]]'
tags:
  - llm-temp-introspection
  - UT
  - PW
---

## 因子
| 因子 | 値1 | 値2 | 値3 |
|---|---|---|---|
| [[RQ-GL-002|run]]終状態 | SUCCEEDED | PARTIAL | FAILED |
| parse failure率 | 0% | 1-5% | >5% |
| 通知有効化 | 有効 | 無効 | - |

## ペアワイズケース
| ケース | [[RQ-GL-002|run]]終状態 | parse failure率 | 通知有効化 | 期待 |
|---|---|---|---|---|
| PW-MON-01 | SUCCEEDED | 0% | 有効 | 完了メトリクス + 完了通知 |
| PW-MON-02 | PARTIAL | 1-5% | 有効 | parse系メトリクス + 警告 |
| PW-MON-03 | FAILED | >5% | 有効 | failureメトリクス + 失敗通知 |
| PW-MON-04 | SUCCEEDED | >5% | 無効 | メトリクスのみ |

## 変更履歴
- 2026-02-28: 初版作成（監視送信条件の2-wiseを定義） [[RQ-RDR-002]]
