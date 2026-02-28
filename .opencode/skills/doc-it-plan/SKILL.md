---
name: doc-it-plan
description: IT-PLAN（結合テスト計画）文書を新規作成・改訂するときに、diopside規約準拠で作成・更新する
metadata:
  short-description: IT-PLAN 文書の更新ガイド
---

## 目的
- diopside の IT-PLAN（結合テスト計画）文書を、Obsidian運用規約に沿って新規作成・改訂する。

## このスキルを使う時
- IT-PLAN を新規作成するとき。
- 結合テストの対象範囲、実施体制、実施順序、合否判定基準を更新するとき。

## このスキルを使わない時
- 個別テストケースの手順・期待結果を更新したいだけのとき（`doc-it-case` を使う）。
- 環境条件やテストデータのみを更新したいとき（`doc-it-env` / `doc-it-tdat` を使う）。

## 出力契約
- 出力は IT-PLAN 1文書に対する最小差分の更新案とし、対象外の文書IDや別種文書テンプレートを混在させない。
- 変更後の文書は `id` とファイル名が一致し、`up/related` でトレース可能な状態にする。

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
- 変更後に `python3 .opencode/skills/obsidian-doc-new/scripts/auto_link_glossary.py <対象Markdownパス>` を実行し、用語（`RQ-GL-*`）をObsidianリンクへ自動変換する。
- 変更後に `python3 .opencode/skills/obsidian-doc-check/scripts/validate_vault.py --docs-root docs --report reports/doc_check.md` を実行し `reports/doc_check.md` を更新する。
