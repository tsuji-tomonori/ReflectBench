---
name: obsidian-trace
description: Obsidian文書のリンク整合や要求-設計の追跡性を確認したいときに、up/related からトレーサビリティをツリー/CSVで生成する
metadata:
  short-description: Obsidian文書のリンク整合や追跡性確認時に、up/relatedからトレーサビリティを生成する
---

## 目的
Obsidianの `up/related` を利用して、指定IDからトレーサビリティを生成します。
（静的なRTMを手更新せず、必要なときに生成する用途）

## 使い方
- ツリー（Markdown）:
  - `python .opencode/skills/obsidian-trace/scripts/traceability.py --start RQ-FR-001 --depth 4 --direction both --include-related --mode tree --out reports/trace_RQ-FR-001.md`
- エッジ一覧（CSV）:
  - `python .opencode/skills/obsidian-trace/scripts/traceability.py --start RQ-FR-001 --depth 4 --direction both --include-related --mode csv --out reports/trace_edges_RQ-FR-001.csv`

## 使う条件
- 指定ID（例: RQ/BD/DD）の `up/related` を起点に、影響範囲や参照抜けを確認したいとき
- レビューや変更影響分析で、手作業のRTM更新ではなく最新リンク状態から再生成したいとき

## 使わない条件
- 本文中の `[[...]]` リンクも含めて網羅的に解析したいとき（本スクリプトはFrontmatterのみ対象）
- 要求の妥当性や設計内容そのものを評価したいとき（本スキルはリンク追跡の可視化が対象）

## 出力契約
- `--mode tree`: Markdownで親子トレースを出力し、各ノードは文書IDで表現する
- `--mode csv`: `from,to,kind` のエッジ一覧を出力し、`kind` は `up` または `related` を取る
- 生成結果は入力VaultのFrontmatterリンク状態に依存し、リンク欠落時は欠落したまま出力される

## 注意
- 出力は **Frontmatterのリンク**のみを使います（本文中リンクは解析しません）
- `--include-related` を付けると、横断リンクも辿ります（ノイズが増える場合あり）
