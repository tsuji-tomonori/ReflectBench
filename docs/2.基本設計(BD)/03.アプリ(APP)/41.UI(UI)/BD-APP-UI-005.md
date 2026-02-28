---
id: BD-APP-UI-005
title: UIコンポーネント構成マトリクス
doc_type: UI設計
phase: BD
version: 1.0.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-27
updated: '2026-02-28'
up:
- '[[BD-APP-UI-001]]'
- '[[BD-APP-UI-002]]'
related:
- '旧参照'
- '[[BD-APP-UI-006]]'
- '[[BD-APP-UI-007]]'
- '[[BD-APP-UI-008]]'
- '[[BD-APP-UI-009]]'
- '[[BD-APP-UI-010]]'
- '[[BD-APP-UI-011]]'
- '[[BD-APP-UI-012]]'
- '[[BD-APP-UI-013]]'
- '[[BD-APP-UI-014]]'
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
- UI設計は「画面コンポーネント」と「UIプリミティブ」を分離し、1コンポーネント1文書で管理する。
- 画面導線は維持しつつ、再利用部品の責務を先に固定して差分実装時の揺れを防ぐ。

## 画面-部品対応
| 画面ID | 画面名 | 主要画面コンポーネント | 主要UIプリミティブ |
| --- | --- | --- | --- |
| UI-U01 | 一覧画面 | [[BD-APP-UI-007|ArchiveList]] | [[BD-APP-UI-012|Button]], [[BD-APP-UI-013|TagButton]], [[BD-APP-UI-015|StatusToast]] |
| UI-U02 | 検索・絞り込み | [[BD-APP-UI-006|SearchConditionPanel]] | [[BD-APP-UI-012|Button]], [[BD-APP-UI-013|FilterChip]], [[BD-APP-UI-014|SearchInput/SelectField/RangeSlider]] |
| UI-U03 | 詳細モーダル | [[BD-APP-UI-008|ArchiveDetailModal]], [[BD-APP-UI-009|HighlightWavePanel]], [[BD-APP-UI-010|WordCloudPanel]] | [[BD-APP-UI-011|ModalActionBar]], [[BD-APP-UI-015|StatusBanner]] |
| UI-A02 | 実行監視・履歴 | [[BD-APP-UI-011|RunStatusScreen]] | [[BD-APP-UI-012|Button]], [[BD-APP-UI-015|StatusBanner]] |

## 変更履歴
- 2026-02-27: 新規作成（UIコンポーネント構成マトリクスを追加） 旧参照