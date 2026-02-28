---
id: RQ-DG-001
title: ドキュメント更新フロー
doc_type: ドキュメント運用ガイド
phase: RQ
version: 1.0.1
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-02-28'
up:
  - '[[RQ-PP-001]]'
related:
  - '[[RQ-RDR-001]]'
  - '[[RQ-RDR-002]]'
  - '[[RQ-SC-001]]'
  - '[[RQ-GL-001]]'
  - '[[RQ-FR-001]]'
  - '[[RQ-AV-001-01]]'
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
  - '[[DD-INF-OVR-001]]'
  - '[[DD-INF-API-001]]'
  - '[[DD-INF-DATA-001]]'
  - '[[DD-INF-IAM-001]]'
  - '[[DD-INF-MON-001]]'
  - '[[DD-INF-PIPE-001]]'
  - '[[DD-APP-OVR-001]]'
  - '[[DD-APP-MOD-001]]'
  - '[[DD-APP-API-001]]'
  - '[[DD-APP-DATA-001]]'
  - '[[DD-APP-ERR-001]]'
tags:
  - llm-temp-introspection
  - RQ
  - DG
---

## 改修フロー（工程別）
### RQ
1. 要求の意味変更時は、同一変更で関連 BD / DD へのリンクを更新する。
2. RQ 文書の `## 変更履歴` は、同一変更内の関連文書 ID を含めて記録する。
3. SC/GL/UC/FR/NFR を追加・変更した場合は、`docs/index.md` の入口導線を同一変更で更新する。

### BD
1. デプロイ方針変更時は `BD-INF-DEP-001` / `BD-INF-DEP-002` を同一変更で更新する。
2. 採用モデル、リージョン、費用前提を変更した場合は DD/OPSREL へ反映する。

### DD
1. durable step、[[RQ-GL-005|manifest]] 仕様、retry 条件を変更した場合は運用ランブックも同一変更で更新する。
2. `strict JSON + Pydantic` の [[RQ-GL-012|canonical schema]] を変更する場合は影響を `related` で追跡する。

### UT/IT/AT
1. デプロイ手順や障害対応に影響する変更では、検証手順書を同時更新する。
2. CI/CD 変更は docs 検証フロー（guard/check）との整合を維持する。

### 共通
1. 文書更新後に用語リンク補正と vault 検証を実行する。
2. 文書運用ルール変更時は `.opencode/skills/doc-bd-dep` / `.opencode/skills/doc-dd-dep` を同一変更で更新する。

## 受入基準
- Frontmatter 必須キー（`id/title/doc_type/phase/version/status/owner/created/updated/up/related/tags`）が欠落していない。
- `filename == id` を満たす。
- 本文中の文書参照は Obsidian リンク（`[[ID]]`）で表記される。
- 更新内容が BD / DD / OPSREL まで追跡可能である。

## 変更履歴
- 2026-02-28: DD-INF/DD-APP 正本分離に合わせて追跡リンクを拡張 [[RQ-RDR-002]]
- 2026-02-28: SC/GL/UC/FR/NFR 追加運用ルールを追記 [[RQ-RDR-002]]
- 2026-02-28: 初版作成（diopside の文書運用ルールを本プロジェクト向けに適用） [[RQ-RDR-001]]
