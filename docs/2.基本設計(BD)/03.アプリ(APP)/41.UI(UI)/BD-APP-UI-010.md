---
id: BD-APP-UI-010
title: WordCloudPanel
doc_type: UI設計
phase: BD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-27
updated: '2026-02-28'
up:
- '[[BD-APP-UI-002]]'
- '[[BD-APP-UI-004]]'
related:
- '旧参照'
- '[[BD-APP-UI-015]]'
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
- `WordCloudPanel` は詳細モーダル内の補助情報表示として定義する。
- 画像依存を避けるため、代替テキストと状態文言を必須化する。

## 設計要点
- 表示成功時は画像と説明文を併置する。
- 404/5xx/破損の状態を分離し、再試行可否を明示する。
- 状態通知は `[[BD-APP-UI-015|StatusBanner]]` と連動し、読み上げ環境へ通知する。

## 入出力境界
- 入力: `video_id`、画像URL、取得状態。
- 出力: `retry()`。

## 変更履歴
- 2026-02-27: 新規作成（ワードクラウドの表示/代替/再試行仕様を部品化） 旧参照