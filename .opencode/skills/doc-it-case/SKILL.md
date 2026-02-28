---
name: doc-it-case
description: IT-CASE（結合テストケース）文書を新規作成・改訂するときに、API/連携単位の手順と期待結果をdiopside規約準拠で整備する
metadata:
  short-description: IT-CASE 文書の更新ガイド
---

## 目的
- diopside（白雪 巴 公開YouTubeアーカイブ収集・蓄積・検索）の文書を、Obsidian運用規約に沿って更新する。

## このスキルを使う条件
- `IT-CASE-*` の新規作成、または既存ケースの手順・期待結果・前提条件を更新するとき。
- `[[IT-PLAN-*]]` や `[[DD-API-*]]` の変更に追従して、結合テストケースの内容を同期するとき。

## このスキルを使わない条件
- 結合テスト計画全体（方針/体制/対象範囲）を更新したいだけの場合（`doc-it-plan` を使う）。
- 結合テスト結果の実績記録を更新する場合（`doc-it-rst` を使う）。

## 出力契約
- 出力対象は `docs/5.結合テスト(IT)/21.結合テストケース(CASE)/IT-CASE-*.md` の単一文書とし、`filename == id` を維持する。
- 本文には少なくとも `対象UC` `対象契約` `生成元PWモデル` `テスト目的` `因子（機能要件ベース）` `テストケース一覧` `手順` `受入接続` を含める。
- `up` には `[[IT-PLAN-*]]` と必要な `[[DD-API-*]]` を設定し、`related` には受入シナリオ（`[[AT-SCN-*]]`）等の接続先を設定する。

## 何を書くべきか
- 文書IDに対応する1トピックの内容。
- Frontmatter必須キー（id/title/doc_type/phase/version/status/owner/created/updated/up/related/tags）。
- 要求または設計の意図、受入条件、関連リンク。
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
- `対象UC` と `生成元PWモデル` が同一ケース内で矛盾しないことを確認する。
- `因子（機能要件ベース）` の各行に `RQ-FR-*` など要求IDが明記されていることを確認する。
- 変更後に `python3 .opencode/skills/obsidian-doc-new/scripts/auto_link_glossary.py <対象Markdownパス>` を実行し、用語（`RQ-GL-*`）をObsidianリンクへ自動変換する。
- 変更後に `python3 .opencode/skills/obsidian-doc-check/scripts/validate_vault.py --docs-root docs --report reports/doc_check.md` を実行し `reports/doc_check.md` を更新する。
