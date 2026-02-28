---
id: BD-APP-UI-009
title: HighlightWavePanel
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
- `HighlightWavePanel` は見どころ導線を提供する補助コンポーネントとして定義する。
- 取得失敗や未生成でも詳細モーダルの主操作を止めない。

## 設計要点
- 波形表示と区間リストの二重表現で、視覚依存を回避する。
- 区間クリックは `t=<秒>` 付き外部遷移に接続する。
- 状態（未生成/失敗/不正）は色以外の文言で明確化する。

## 入出力境界
- 入力: `video_id`、波形データ、取得状態。
- 出力: `openAt(second)`、`retry()`。

## 変更履歴
- 2026-02-27: 新規作成（コメント密度波形の補助導線仕様を部品化） 旧参照