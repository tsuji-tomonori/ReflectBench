# Document Template

## 本文
- このテンプレートは Bedrock Batch + Durable 構成の BD-DEP 下書き。
- Frontmatter は文書IDに合わせて設定する。

## 必須観点
- 目的と対象範囲（Study1/2 + 実験A/D）
- リージョン/モデルID固定方針
- 実行基盤（API Gateway/Lambda/S3/Bedrock Batch/CloudWatch）
- CDK決定性方針（`synth` 副作用ゼロ、props注入、durable事前有効化）
- 費用前提と支配コスト
- 受入条件

## 変更履歴
- YYYY-MM-DD: 変更要約
