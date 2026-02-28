---
id: UT-PW-APP-DATA-001
title: データ正規化条件ペアワイズ
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
  - '[[UT-CASE-APP-004]]'
  - '[[UT-CASE-APP-005]]'
  - '[[UT-CASE-APP-006]]'
  - '[[DD-APP-DATA-001]]'
tags:
  - llm-temp-introspection
  - UT
  - PW
---

## 因子
| 因子 | 値1 | 値2 | 値3 |
|---|---|---|---|
| JSON構文 | 正常 | 破損 | - |
| schema適合 | 適合 | 必須欠損 | 型不一致 |
| record_id入力 | 完備 | 一部欠落 | - |

## ペアワイズケース
| ケース | JSON構文 | schema適合 | record_id入力 | 期待 |
|---|---|---|---|---|
| PW-DATA-01 | 正常 | 適合 | 完備 | `normalized/` |
| PW-DATA-02 | 正常 | 必須欠損 | 完備 | `invalid/` |
| PW-DATA-03 | 正常 | 型不一致 | 完備 | `invalid/` |
| PW-DATA-04 | 破損 | 必須欠損 | 完備 | parse error |
| PW-DATA-05 | 正常 | 適合 | 一部欠落 | ID生成中断 |

## 変更履歴
- 2026-02-28: 初版作成（正規化処理の2-wiseを定義） [[RQ-RDR-002]]
