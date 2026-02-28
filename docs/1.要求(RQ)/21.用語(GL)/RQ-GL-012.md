---
id: RQ-GL-012
title: canonical schema
term_en: canonical_schema
doc_type: 用語
phase: RQ
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SC-001]]'
related: []
tags:
  - llm-temp-introspection
  - RQ
  - GL
---

## 定義
| 項目 | 内容 |
|---|---|
| 用語ID | `RQ-GL-012` |
| 用語名 | [[RQ-GL-012|canonical schema]] |
| 英名 | `canonical_schema` |
| 定義 | 正規化後の共通データ契約（Study1Record, PredictionRecord 等）。 |
| 判定条件/適用範囲 | strict JSON + Pydantic 検証後の保存形式。 |

## 変更履歴
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
