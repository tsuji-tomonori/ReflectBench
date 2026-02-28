---
id: UT-PW-001
title: ペアワイズ設計一覧（run実行基盤）
doc_type: ペアワイズ設計
phase: UT
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[UT-PLAN-001]]'
related:
  - '[[UT-PW-BE-API-001]]'
  - '[[UT-PW-APP-ORCH-001]]'
  - '[[UT-PW-APP-DATA-001]]'
  - '[[UT-PW-APP-ERR-001]]'
  - '[[UT-PW-APP-MON-001]]'
tags:
  - llm-temp-introspection
  - UT
  - PW
---

## 目的
- 組合せ起因の回帰を 2-wise で効率的に検出する。

## 対象マトリクス
- BE API 入力条件
- APP orchestration 条件
- APP データ正規化条件
- APP エラー分類条件
- APP 監視送信条件

## 実施方針
- 3因子以上の条件分岐を持つ対象は pairwise ケースを必須化する。
- 期待結果は対応する `UT-CASE-*` の受入条件と整合させる。

## 変更履歴
- 2026-02-28: 初版作成（[[RQ-GL-002|run]]基盤向けペアワイズ設計を追加） [[RQ-RDR-002]]
