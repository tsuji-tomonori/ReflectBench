---
name: doc-dd-dep
description: DD-DEP（デプロイ詳細設計）文書を新規作成・改訂するときに、本リポジトリ規約準拠で作成・更新する
metadata:
  short-description: DD-DEP 文書の更新ガイド
---

## 目的
- Bedrock Batch 実行の step 詳細、manifest 仕様、retry/障害対応を再現可能なDDとして管理する。

## このスキルを使う条件
- DDフェーズのデプロイ詳細（durable step、Batch投入、poll、正規化、集計）を更新するとき。
- BD変更を受けて実行パラメータ、監視項目、運用制約を具体化するとき。

## このスキルを使わない条件
- 方針レベルのみのBD更新。
- 推論ロジックそのもののアルゴリズム改修。

## 何を書くべきか
- Frontmatter 必須キー（`id/title/doc_type/phase/version/status/owner/created/updated/up/related/tags`）。
- durable step 定義（0-9）、入出力キー、canonical schema、deterministic ID。
- retry 方針、`invalid/` 退避、アラーム条件、run 完了判定。
- `## 変更履歴` への当日追記。

## 何を書かないべきか
- 複数トピックの混在。
- 本文での上位/下位文書セクション。
- 実運用と乖離した暫定コマンド列。

## 出力契約
- `filename == id` を満たす。
- `up/related` で BD と OPSREL へ追跡可能にする。
- パラメータ表（region/shard/poll/timeout/retry）が本文と矛盾しない。

## 品質チェック
- 用語リンク補正: `python3 .opencode/skills/obsidian-doc-new/scripts/auto_link_glossary.py <対象Markdownパス>`
- vault検証: `python3 .opencode/skills/obsidian-doc-check/scripts/validate_vault.py --docs-root docs --report reports/doc_check.md`
