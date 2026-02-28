# Document Template

## 本文
- このテンプレートは Bedrock Batch + Durable 構成の DD-DEP 下書き。
- Frontmatter は文書IDに合わせて設定する。

## 必須観点
- durable step（start -> enumerate -> submit -> poll -> normalize -> report）
- モデルルーティングと manifest 出力先
- strict JSON + Pydantic 検証と `invalid/` 退避
- retry 条件（job failure / parse failure / orchestrator failure）
- 監視・通知・運用確認手順
- 受入条件

## 変更履歴
- YYYY-MM-DD: 変更要約
