---
name: doc-rq-uc
description: doc-rq-uc に対応するユースケース要求（RQ-UC）文書を、追加・変更・レビュー時に規約準拠で作成・更新する
metadata:
  short-description: RQ-UC 文書の更新ガイド
---

## 目的
- diopside（白雪 巴 公開YouTubeアーカイブ収集・蓄積・検索）の文書を、Obsidian運用規約に沿って更新する。

## このスキルを使う条件
- `docs/1.要求(RQ)/31.ユースケース(UC)` 配下の文書を新規作成・改訂する。
- `概要/基本フロー/代替・例外フロー` のうち、ユースケース固有の振る舞いを追加・変更する。
- ユースケース要求の意味変更があり、関連文書とのトレーサビリティ確認が必要になる。

## このスキルを使わない条件
- FR/NFRや設計文書（BD/DD）を更新するだけで、RQ-UCを変更しない。
- 文言修正のみで、ユースケースの振る舞い・受入条件・例外条件に変更がない。

## 出力契約
- 対象 `RQ-UC-*` 文書が、必須Frontmatterと `概要/基本フロー/代替・例外フロー` を満たした状態で更新されている。
- `up/related` が有効なObsidianリンクになっており、関連要求との追跡経路が維持されている。
- 用語リンク補正と `validate_vault.py` 実行後、検証結果が `reports/doc_check.md` に反映されている。

## 何を書くべきか
- 文書IDに対応する1トピックの内容。
- Frontmatter必須キー（id/title/doc_type/phase/version/status/owner/created/updated/up/related/tags）。
- 要求または設計の意図、受入条件、関連リンク。
- `概要/基本フロー/代替・例外フロー` をユースケース固有の内容で記述する。
- 主体はアクター目的主体（`[[RQ-SH-*|...]]が〜する`）で記述し、`システムは` 主体の表現を使わない。
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
- `基本フロー` がテンプレート文（例: 「操作を開始する」「入力を検証し、処理を実行する」）のまま残っていない。
- `代替/例外フロー` がユースケース固有の例外を2件以上持つ。
- 本文がアクター目的主体で記述され、`システムは` 主体へ回帰していないことを確認する。
- 変更後に `python3 .opencode/skills/obsidian-doc-new/scripts/auto_link_glossary.py <対象Markdownパス>` を実行し、用語（`RQ-GL-*`）をObsidianリンクへ自動変換する。
- 変更後に `python3 .opencode/skills/obsidian-doc-check/scripts/validate_vault.py --docs-root docs --report reports/doc_check.md` を実行し `reports/doc_check.md` を更新する。
