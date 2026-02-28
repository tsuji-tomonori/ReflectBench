---
name: doc-bd-dep
description: BD-DEP（デプロイ基本設計）文書を新規作成・改訂するときに、本リポジトリ規約準拠で作成・更新する
metadata:
  short-description: BD-DEP 文書の更新ガイド
---

## 目的
- Bedrock Batch + Lambda Durable Functions 前提のデプロイ基本設計を、Obsidian運用規約に沿って更新する。

## このスキルを使う条件
- BDフェーズのデプロイ設計（リージョン選定、配備境界、実行チェーン、費用見積）を更新するとき。
- `plan.md` の前提変更により採用モデル、実行順序、CI/CDゲートを更新するとき。

## このスキルを使わない条件
- DD実装手順のみを更新する作業。
- API契約や分析ロジックなど、デプロイ基本設計を主題としない文書更新。

## 何を書くべきか
- Frontmatter 必須キー（`id/title/doc_type/phase/version/status/owner/created/updated/up/related/tags`）。
- 単一リージョン設計、採用モデルID、実行基盤、リソース責務、費用前提。
- CDK方針（`synth` 決定性、環境差分の props 注入、durable 事前有効化）。
- `## 変更履歴` への当日追記。

## 何を書かないべきか
- 複数トピックの混在。
- 本文での上位/下位文書セクション。
- Mermaid 以外の図式表現。

## 出力契約
- `filename == id` を満たす。
- `up/related` で DD / OPSREL まで追跡可能にする。
- 採用モデルIDとリージョンが本文と表で矛盾しない。

## 品質チェック
- 用語リンク補正: `python3 .opencode/skills/obsidian-doc-new/scripts/auto_link_glossary.py <対象Markdownパス>`
- vault検証: `python3 .opencode/skills/obsidian-doc-check/scripts/validate_vault.py --docs-root docs --report reports/doc_check.md`
