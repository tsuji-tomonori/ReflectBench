---
id: RQ-RDR-001
title: 文書運用方式の採用（Obsidianリンク + docs:guard）
doc_type: 要求決定記録
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-DG-001]]'
related:
  - '[[RQ-PP-001]]'
  - '[[RQ-RDR-002]]'
  - '[[BD-SYS-ADR-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - RDR
---

## 決定
- 文書管理は 1トピック1ファイル、`filename == id`、Obsidianリンク（`[[ID]]`）を基本規約として採用する。
- 文書品質ゲートとして `docs:guard`（auto-link + validate）を標準入口に採用する。

## 根拠
- デプロイ設計と運用設計を段階的に増やすため、IDリンクによる追跡性が必要。
- `plan.md` に基づく実験フェーズの変更頻度が高く、機械検証可能な frontmatter 規約が必要。

## 影響
- RQ/BD/DD/OPSREL 文書の変更時に、frontmatter 検証とリンク検証を必須化する。
- `.opencode/skills` の `doc-bd-dep` / `doc-dd-dep` を更新対象に含める。
- 正本分担（infra=`plan.md`, experiment=`.ai_workspace/llm-temp-introspection`）の運用決定は [[RQ-RDR-002]] を参照する。

## 変更履歴
- 2026-02-28: 正本分担ルール決定（[[RQ-RDR-002]]）への参照導線を追加 [[RQ-RDR-002]]
- 2026-02-28: 初版作成（文書運用と検証ゲートの採用を決定） [[RQ-RDR-001]]
