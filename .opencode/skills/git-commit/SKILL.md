---
name: git-commit
description: diopside文書変更をコミットする際に、日本語のConventional Commitsを作成する
metadata:
  short-description: diopside向けコミット規約
---

## 形式
- `type(scope): subject`
- type: feat / fix / docs / refactor / test / chore
- subject と本文は日本語で記述する

## diopside運用の適用
- 文書更新は `docs(...)` または `docs(docs)` を基本とする
- レポート更新は `docs(reports)` を使用する
- スキル更新は `chore(skills)` を使用する
- 規約変更に伴う運用更新は `chore(docops)` を優先する

## scopeの目安
- 単一文書: `docs(RQ-SC-001)`
- 同一系統の複数文書: `docs(RQ)` / `docs(DD-API)`
- 監査・確認系: `docs(reports)`
- 補助設定・自動化: `chore(skills)` / `chore(tooling)`

## 方針
- 変更の意図（why）を優先して記載する
- 1コミット1意図を意識し、差分のまとまりを崩さない
- セキュリティ情報や秘密情報は含めない

## 使う条件
- diopside文書（`docs/**` や `reports/**`）の変更をコミットする
- scopeを文書ID/系統/運用区分で表現し、規約に沿って統一したい

## 使わない条件
- ソースコード主体の機能開発で、文書運用用scopeよりコード領域scopeを優先すべき
- コミットを行わず、レビューコメントや作業メモのみを作成する

## 出力契約
- 出力は `type(scope): subject` 形式のコミットメッセージ案とする
- `subject` と必要な本文は日本語で、変更理由（why）を1-2文で示す
- 規約変更を伴う場合は `chore(docops)` を優先候補として明示する

## 例
- `docs(RQ-SC-001): 収集対象の区分定義を公開アーカイブ前提で明確化`
- `docs(reports): 影響確認結果と手動doc check結果を更新`
- `chore(skills): diopside運用に合わせてgit-commitスキルを調整`
