---
id: UT-PW-APP-ORCH-001
title: orchestration 条件ペアワイズ
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
  - '[[UT-CASE-APP-001]]'
  - '[[UT-CASE-APP-002]]'
  - '[[UT-CASE-APP-003]]'
  - '[[DD-APP-MOD-001]]'
tags:
  - llm-temp-introspection
  - UT
  - PW
---

## 因子
| 因子 | 値1 | 値2 | 値3 |
|---|---|---|---|
| step失敗位置 | なし | Study2 | 実験D |
| retry可否 | 可 | 不可 | - |
| parse failure率 | 0% | 1-5% | >5% |

## ペアワイズケース
| ケース | step失敗位置 | retry可否 | parse failure率 | 期待 |
|---|---|---|---|---|
| PW-ORCH-01 | なし | 可 | 0% | `SUCCEEDED` |
| PW-ORCH-02 | Study2 | 可 | 1-5% | retry後継続 |
| PW-ORCH-03 | Study2 | 不可 | 0% | `FAILED` |
| PW-ORCH-04 | 実験D | 可 | >5% | `PARTIAL` または `FAILED` |
| PW-ORCH-05 | なし | 不可 | >5% | `PARTIAL` |

## 変更履歴
- 2026-02-28: 初版作成（orchestration 2-wiseを定義） [[RQ-RDR-002]]
