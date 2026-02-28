---
id: BD-APP-UI-011
title: RunStatusScreen
doc_type: UI設計
phase: BD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-27
updated: '2026-02-28'
up:
- '[[BD-APP-UI-001]]'
- '[[BD-APP-UI-003]]'
related:
- '旧参照'
- '旧参照'
- '旧参照'
- '旧参照'
- '[[BD-APP-UI-012]]'
- '[[BD-APP-UI-015]]'
tags:
- llm-temp-introspection
- BD
- UI
---

## スコープ注記
- 本文書は `docs/2.基本設計(BD)/03.アプリ(APP)` の旧文脈文書を保持する参考文書であり、現行スコープの正本ではない。
- 現行スコープの正本は `[[RQ-SC-001]]` と DD-INF/DD-APP 系列を優先する。


## 設計方針
- `RunStatusScreen` は管理導線の監視ハブとして [[RQ-GL-002|run]] 状態と再試行判断を集約する。
- 失敗時でも [[RQ-GL-002|run]] 単位の追跡可能性を維持し、復帰導線を固定する。

## 設計要点
- 状態モデルは `queued/running/succeeded/failed` を基本値とする。
- `running` 中は再実行操作を表示しない。
- 連続失敗時は `[[BD-APP-UI-015|StatusBanner]]` を固定表示し、次操作を提示する。

## 入出力境界
- 入力: [[RQ-GL-002|run]]一覧、選択[[RQ-GL-002|run]]、失敗分類、再試行可否。
- 出力: `selectRun(runId)`、`retryRun(runId)`、`refresh()`。

## 変更履歴
- 2026-02-27: 新規作成（管理[[RQ-GL-002|run]]監視画面の責務と状態境界を定義） 旧参照
