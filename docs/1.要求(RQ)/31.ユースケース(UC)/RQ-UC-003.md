---
id: RQ-UC-003
title: 失敗runを復旧する
doc_type: ユースケース
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-SH-001]]'
related:
  - '[[RQ-FR-012]]'
  - '[[RQ-FR-013]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-APP-MOD-001]]'
  - '[[DD-APP-ERR-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - UC
---

## シナリオ
1. 失敗した [[RQ-GL-004|shard]] または parse failure を確認する。
2. [[RQ-GL-004|shard]] 再試行または `invalid/` 退避で復旧する。
3. [[RQ-GL-002|run]] [[RQ-GL-005|manifest]] に復旧結果を記録する。

## 受入条件
- 復旧手順が [[RQ-GL-002|run]] 単位で再現できる。

## 変更履歴
- 2026-02-28: 復旧ユースケースの DD-INF/DD-APP 追跡リンクを追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成 [[RQ-RDR-002]]
