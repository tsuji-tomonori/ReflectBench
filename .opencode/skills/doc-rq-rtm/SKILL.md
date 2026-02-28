---
name: doc-rq-rtm
description: doc-rq-rtm に対応するdiopsideの要求トレーサビリティマトリックス（RQ-RTM）文書を規約準拠で作成・更新し、Quartz公開可能な静的追跡性と関連文書整合を確認する。RQ-RTM文書の追加・変更・レビュー時に使う
metadata:
  short-description: RQ-RTM 文書の更新ガイド
---

## 目的
- diopside（白雪 巴 公開YouTubeアーカイブ収集・蓄積・検索）の文書を、Obsidian運用規約に沿って更新する。

## 何を書くべきか
- 文書IDに対応する1トピックの内容。
- Frontmatter必須キー（id/title/doc_type/phase/version/status/owner/created/updated/up/related/tags）。
- 要求または設計の意図、受入条件、関連リンク。
- Quartzで表示可能な静的追跡方針（どの要求群を、どのリンク軸で可視化するか）と、運用時の参照手順。
- `## 変更履歴` への当日追記。

## 何を書かないべきか
- 複数トピックの混在。
- 本文での上位/下位セクション（関係はfrontmatterのみ）。
- Mermaid以外の図表形式。

## Frontmatter運用
- `phase` は ID prefix と一致させる。
- `owner` は `RQ-SH-*` を使う。
- 意味変更時は `version` をPATCH更新する。
- `updated` は作業日へ更新する。

## 品質チェック
- `filename == id` を維持する。
- `up/related` のリンク先が存在することを確認する。
- 手更新の固定マトリックスを本文に持ち込まず、リンク正本から静的再生成できる形を維持する。
- 要求別（RQ起点）と設計別（BD/DD起点）の両ビューが、Quartz上で参照可能なMarkdownとして成立していることを確認する。
- 変更後に `task docs:trace` を実行し、`RQ-RTM-001` / `RQ-RTM-002` の自動生成ブロックを更新する。
- 変更後に `python3 .opencode/skills/obsidian-doc-new/scripts/auto_link_glossary.py <対象Markdownパス>` を実行し、用語（`RQ-GL-*`）をObsidianリンクへ自動変換する。
- 変更後に `python3 .opencode/skills/obsidian-doc-check/scripts/validate_vault.py --docs-root docs --report reports/doc_check.md` を実行し `reports/doc_check.md` を更新する。

## 使う条件
- RQ-RTM 文書を新規作成・更新・レビューし、要求群のトレーサビリティ表示条件（静的Markdown）を定義または調整するとき。
- RQ文書の追加/変更に伴い、追跡ビューの再生成結果と `up/related` の整合を同一変更で確認したいとき。

## 使わない条件
- コード実装のみで、docs/Obsidian文書を更新しないとき。
- 固定表の手入力でトレーサビリティを管理し、静的再生成可能性を前提にしないとき。

## 出力契約
- 更新対象の RQ-RTM 文書に、Quartz表示可能な静的追跡方針と抽出条件が再利用可能な形で記述されていること。
- 変更理由の要約と、実施した検証（リンク確認・整合チェック）の結果。
