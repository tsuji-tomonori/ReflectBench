---
id: BD-APP-UI-015
title: StatusToastとStatusBanner
doc_type: UI設計
phase: BD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-27
updated: '2026-02-28'
up:
- '[[BD-APP-UI-004]]'
- '[[BD-APP-UI-005]]'
related:
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
- 本文中の「旧参照」は、現行リポジトリに存在しない旧要求/旧設計IDを示す。


## 設計方針
- 処理結果通知は `StatusToast`（一時通知）と `StatusBanner`（継続通知）を使い分ける。
- 通知はフォーカス移動に依存せず、支援技術へ同時通知する。

## 設計要点
- `StatusToast`
  - 成功/軽微失敗/補助操作結果を短く通知。
  - 自動消去時も履歴または再確認導線を持つ。
- `StatusBanner`
  - 連続失敗や運用判断が必要な状態を表示。
  - 「結果 + 原因 + 次操作」を1ブロックで提示。

## 受入条件
- `role="status"` または `aria-live` を必須で付与する。
- 色だけでなく文言またはアイコンを併用する（旧参照）。
- 通知表示中でも主要操作を阻害しない。

## 変更履歴
- 2026-02-27: 新規作成（状態通知コンポーネントの役割と通知規約を定義） 旧参照