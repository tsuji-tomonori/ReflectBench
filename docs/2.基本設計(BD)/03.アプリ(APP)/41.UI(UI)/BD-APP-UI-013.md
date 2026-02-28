---
id: BD-APP-UI-013
title: FilterChipとTagButton
doc_type: UI設計
phase: BD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-27
updated: '2026-02-28'
up:
- '[[BD-APP-UI-005]]'
- '[[BD-APP-UI-007]]'
related:
- '[[RQ-FR-010]]'
- '旧参照'
- '旧参照'
- '旧参照'
- '旧参照'
- '[[BD-APP-UI-016]]'
tags:
- llm-temp-introspection
- BD
- UI
---

## スコープ注記
- 本文書は `docs/2.基本設計(BD)/03.アプリ(APP)` の旧文脈文書を保持する参考文書であり、現行スコープの正本ではない。
- 現行スコープの正本は `[[RQ-SC-001]]` と DD-INF/DD-APP 系列を優先する。


## 設計方針
- タグ操作は `FilterChip`（条件一覧側）と `TagButton`（カード側）で役割を分離する。
- 選択状態は色に加えてテキスト変化と状態属性で伝える。

## 設計要点
- `FilterChip`
  - 既に選択されたタグの解除操作に特化。
  - ラベル末尾に解除記号を表示し、解除意図を明示。
- `TagButton`
  - 動画カード内タグの選択/解除操作に特化。
  - `aria-pressed` または `aria-selected` を付与して支援技術へ通知。

## 受入条件
- 選択/非選択の差は色のみで表現しない（文言またはアイコンを併用）。
- クリック/キーボードの両操作で同一結果を返す。

## 変更履歴
- 2026-02-27: 新規作成（タグ操作プリミティブの役割分離を定義） 旧参照
