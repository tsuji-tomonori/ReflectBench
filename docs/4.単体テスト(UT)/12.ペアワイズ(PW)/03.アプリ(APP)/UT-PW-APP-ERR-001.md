---
id: UT-PW-APP-ERR-001
title: エラー分類条件ペアワイズ
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
  - '[[UT-CASE-APP-009]]'
  - '[[DD-APP-ERR-001]]'
tags:
  - llm-temp-introspection
  - UT
  - PW
---

## 因子
| 因子 | 値1 | 値2 | 値3 |
|---|---|---|---|
| category | validation | dependency | timeout |
| step | API | normalize | report |
| 再試行回数 | 0 | 1 | 上限超過 |

## ペアワイズケース
| ケース | category | step | 再試行回数 | 期待 |
|---|---|---|---|---|
| PW-ERR-01 | validation | API | 0 | `retryable=false` |
| PW-ERR-02 | dependency | normalize | 1 | `retryable=true` |
| PW-ERR-03 | timeout | report | 上限超過 | `FAILED` |
| PW-ERR-04 | dependency | API | 上限超過 | `FAILED` |

## 変更履歴
- 2026-02-28: 初版作成（エラー分類の2-wiseを定義） [[RQ-RDR-002]]
