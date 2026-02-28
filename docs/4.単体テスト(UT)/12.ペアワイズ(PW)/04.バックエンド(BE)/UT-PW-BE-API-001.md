---
id: UT-PW-BE-API-001
title: run API 入力条件ペアワイズ
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
  - '[[UT-CASE-BE-001]]'
  - '[[UT-CASE-BE-002]]'
  - '[[UT-CASE-BE-003]]'
  - '[[DD-INF-API-001]]'
tags:
  - llm-temp-introspection
  - UT
  - PW
---

## 因子
| 因子 | 値1 | 値2 | 値3 |
|---|---|---|---|
| `loops` | 10 | 9 | 11 |
| `full_cross` | true | false | - |
| `idempotency_key` | 新規 | 同一再送 | 異条件重複 |

## ペアワイズケース
| ケース | loops | full_cross | idempotency_key | 期待 |
|---|---|---|---|---|
| PW-BE-01 | 10 | true | 新規 | `202` |
| PW-BE-02 | 9 | true | 新規 | `400` |
| PW-BE-03 | 10 | false | 新規 | `400` |
| PW-BE-04 | 10 | true | 同一再送 | 同一 `run_id` |
| PW-BE-05 | 11 | true | 異条件重複 | `400` または `409` |

## 変更履歴
- 2026-02-28: 初版作成（API入力の2-wise組合せを定義） [[RQ-RDR-002]]
