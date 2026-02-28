---
id: BD-APP-UI-006
title: SearchConditionPanel
doc_type: UI設計
phase: BD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-27
updated: '2026-02-28'
up:
- '[[BD-APP-UI-002]]'
- '[[BD-APP-UI-003]]'
related:
- '[[RQ-FR-008]]'
- '[[RQ-FR-010]]'
- '[[RQ-FR-011]]'
- '[[RQ-FR-012]]'
- '旧参照'
- '[[BD-APP-UI-014]]'
tags:
- llm-temp-introspection
- BD
- UI
---

## スコープ注記
- 本文書は `docs/2.基本設計(BD)/03.アプリ(APP)` の旧文脈文書を保持する参考文書であり、現行スコープの正本ではない。
- 現行スコープの正本は `[[RQ-SC-001]]` と DD-INF/DD-APP 系列を優先する。
- 本文中の「旧参照」は、現行リポジトリに存在しない旧要求/旧設計IDを示す。


## 設計方針
- `SearchConditionPanel` は検索語、タグ条件、期間条件、並び順の確定入口を単一化する。
- 同一手続き内の再入力を最小化し、再表示時に直前確定値を復元する（旧参照）。

## 設計要点
- 入力中状態と確定状態を分離し、確定操作前に一覧再読込を発生させない。
- `[[BD-APP-UI-014|SearchInput/SelectField/RangeSlider]]` を内部プリミティブとして利用する。
- ヘルプ導線は「ヘルプ/お問い合わせ」で名称固定し、同位置に配置する（旧参照）。

## 入出力境界
- 入力: 現在検索条件、タグ候補、タグ件数、年別件数。
- 出力: `apply(conditions)`、`clear()`、`validationError(reason)`。

## 変更履歴
- 2026-02-27: 新規作成（検索条件パネルの責務と境界を定義） 旧参照