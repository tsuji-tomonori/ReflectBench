---
id: OPSREL-RUN-001
title: Bedrock Batch 実験運用ランブック
doc_type: 運用ランブック
phase: AT
version: 1.1.0
status: 下書き
owner: RQ-SH-001
created: 2026-02-28
updated: '2026-03-13'
up:
  - '[[DD-INF-DEP-001]]'
  - '[[DD-INF-DEP-002]]'
related:
  - '[[RQ-PP-001]]'
  - '[[RQ-PC-001]]'
  - '[[RQ-UC-003]]'
  - '[[RQ-OBS-001-02]]'
  - '[[BD-INF-DEP-001]]'
  - '[[BD-INF-DEP-002]]'
  - '[[DD-INF-PIPE-001]]'
  - '[[BD-SYS-ADR-001]]'
tags:
  - llm-temp-introspection
  - OPSREL
  - RUN
---

## 目的
- Study1 / Study2 / 追加実験 A / D のフル [[RQ-GL-002|run]] を、失敗時の再試行を含めて運用可能にする。

## 必要時運用
1. `POST /runs` で [[RQ-GL-002|run]] を開始する。
2. `GET /runs/{run_id}` で [[RQ-GL-003|phase]] と進捗を監視する。
3. 完了後 `GET /runs/{run_id}/artifacts` で reports を取得する。
4. 実験継続が不要になった場合は `POST /runs/{run_id}/cancel` で停止要求を出す。

## 実行開始時の確認
- リージョンが `ap-southeast-2` であること。
- editor が `apac.amazon.nova-micro-v1:0` に固定されていること。
- [[RQ-GL-004|shard]] size が 500、poll interval が 180 秒であること。
- output 先 S3 prefix に書き込み権限があること。

## 実行手順（CLI）
### 前提
- AWS 認証済みであること（`aws sts get-caller-identity` が成功すること）。
- 利用ツール: `aws`, `curl`, `jq`, `uv`。
- 変数を設定する。

```bash
set -euo pipefail

export REGION="ap-southeast-2"
export AWS_REGION="$REGION"
```

### デプロイ（必要時）
```bash
uv run --group infra --no-binary cdk deploy --all --require-approval never --app "python3 infra/app.py"
```

### 1) API エンドポイント取得
```bash
API_URL=$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name ExperimentStack \
  --query "Stacks[0].Outputs[?OutputKey=='RunsApiUrl'].OutputValue | [0]" \
  --output text)

echo "API_URL=$API_URL"
```

### 2) フル実験 run 開始
```bash
RUN_ID=$(curl -sS -X POST "$API_URL/runs" \
  -H "content-type: application/json" \
  -d '{
    "loops": 10,
    "full_cross": true,
    "shard_size": 500,
    "poll_interval_sec": 180,
    "editor_model": "apac.amazon.nova-micro-v1:0"
  }' | jq -r '.run_id')

echo "RUN_ID=$RUN_ID"
```

### 3) 完了まで監視（`SUCCEEDED`/`PARTIAL`/`FAILED`/`CANCELLED` で停止）
```bash
while true; do
  STATUS=$(curl -sS "$API_URL/runs/$RUN_ID")
  STATE=$(echo "$STATUS" | jq -r '.state')
  PHASE=$(echo "$STATUS" | jq -r '.phase')
  PERCENT=$(echo "$STATUS" | jq -r '.progress.percent // 0')
  echo "state=$STATE phase=$PHASE progress=${PERCENT}%"
  if [ "$STATE" = "SUCCEEDED" ] || [ "$STATE" = "PARTIAL" ] || [ "$STATE" = "FAILED" ] || [ "$STATE" = "CANCELLED" ]; then
    break
  fi
  sleep 30
done
```

### 3-b) 途中停止が必要になった場合
```bash
curl -sS -X POST "$API_URL/runs/$RUN_ID/cancel" \
  -H "content-type: application/json" \
  -d '{
    "reason": "operator requested stop after anomaly review"
  }' | jq '{run_id, state, cancel}'
```

### 4) 実行結果の確認
```bash
curl -sS "$API_URL/runs/$RUN_ID" | jq '{run_id, state, phase, progress, last_error}'
aws s3 ls "s3://llm-temp-introspection-artifacts/runs/$RUN_ID/" --recursive --region "$REGION"
```

## デバッグ手順
### 0) まず状態を確認
```bash
curl -sS "$API_URL/runs/$RUN_ID" | jq '{state, phase, progress, last_error}'
```

### 1) Orchestrator ログ確認（直近 60 分）
```bash
aws logs tail /aws/lambda/orchestrator_fn \
  --region "$REGION" \
  --since 60m \
  --format short
```

### 2) run_id で Orchestrator ログを絞り込み
```bash
aws logs filter-log-events \
  --region "$REGION" \
  --log-group-name /aws/lambda/orchestrator_fn \
  --filter-pattern "$RUN_ID" \
  --start-time $((($(date +%s)-3600)*1000)) \
  --query 'events[].message' \
  --output text
```

### 3) API ごとの Lambda ログ確認
```bash
# run 投入時
aws logs tail /aws/lambda/start_run_fn \
  --region "$REGION" \
  --since 60m \
  --format short

# status API
aws logs tail /aws/lambda/status_fn \
  --region "$REGION" \
  --since 60m \
  --format short

# artifacts API
aws logs tail /aws/lambda/artifacts_fn \
  --region "$REGION" \
  --since 60m \
  --format short
```

### 4) S3 成果物の進捗確認
```bash
aws s3 ls "s3://llm-temp-introspection-artifacts/runs/$RUN_ID/" --recursive --region "$REGION"
```

### 5) DynamoDB で run 状態を確認
```bash
TABLE_NAME="$(aws cloudformation describe-stacks \
  --stack-name ExperimentStack \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='RunControlTableName'].OutputValue | [0]" \
  --output text)"

# run 一覧（IDEMPOTENCY を除外）
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --projection-expression "run_id,created_at,phase,#st,kind" \
  --expression-attribute-names '{"#st":"state"}' \
  --query 'Items[?kind.S!=`IDEMPOTENCY`].{run_id:run_id.S,created_at:created_at.S,phase:phase.S,state:state.S}' \
  --output table
```

### 6) FAILED run の詳細抽出（last_error）
```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --projection-expression "run_id,created_at,phase,#st,last_error,finished_at,updated_at,kind" \
  --expression-attribute-names '{"#st":"state"}' \
  --filter-expression "#st = :failed AND (attribute_not_exists(kind) OR kind <> :idem)" \
  --expression-attribute-values '{":failed":{"S":"FAILED"},":idem":{"S":"IDEMPOTENCY"}}' \
  --output json \
| jq -r '
  .Items
  | sort_by(.created_at.S) | reverse
  | .[]
  | [
      .created_at.S,
      .run_id.S,
      .phase.S,
      .state.S,
      (.last_error.M.step.S // "-"),
      (.last_error.M.reason.S // "-"),
      (.last_error.M.category.S // "-"),
      ((.last_error.M.retryable.BOOL // false)|tostring),
      (.last_error.M.trace_id.S // "-")
    ]
  | @tsv
'
```

### 典型的な確認順（推奨）
1. `GET /runs/{run_id}` で `state/phase/last_error` を確認する。
2. `orchestrator_fn` ログを `run_id` で絞り、失敗 step を特定する。
3. `start_run_fn` / `status_fn` / `artifacts_fn` の API 側失敗有無を確認する。
4. S3 配下の生成物有無で停止ポイントを特定する。
5. DynamoDB の `last_error` と照合し、再実行可否を判断する。

## 完了判定
- `reports/run_manifest.json` が存在する。
- `study1_summary.csv`, `study2_within.csv`, `study2_across.csv`, `experiment_a.csv`, `experiment_d.csv` が存在する。
- `RunStatus.state` が `SUCCEEDED` である。

## 停止完了判定
- `GET /runs/{run_id}` の `state` が `CANCELLED` である。
- `cancel.requested_at` と停止理由が参照できる。
- 以後 `progress` が進まず、新しい Batch submit が増えない。

## 失敗時対応
### Batch job failure
1. 失敗 [[RQ-GL-004|shard]] を特定する。
2. [[RQ-GL-004|shard]] 単位で 1 回再試行する。
3. 再失敗時は [[RQ-GL-002|run]] を `FAILED` にし、原因を `last_error` へ保存する。

### JSON parse failure
1. 失敗レコードを `invalid/` に退避する。
2. invalid 件数を [[RQ-GL-002|run]] [[RQ-GL-005|manifest]] へ記録する。
3. 後続集計は invalid を除外して継続する。

### Orchestrator failure
1. CloudWatch Logs で failure step を特定する。
2. 入力破損か依存障害かを切り分ける。
3. 再開可能な step から再実行する。

## コスト監視
- 1 [[RQ-GL-002|run]] の目安は Bedrock モデル費 `$2.66`。
- 連続実行時は週次で `run_manifest.json` を集計し、[[RQ-GL-003|phase]] 別コスト比率を確認する。
- Qwen3 32B の output 単価が支配的なため、追加実験 D の件数増加を最優先監視対象にする。

## ドキュメント配信手順（CI/CD骨格）
1. GitHub の `prod` environment に `AWS_ROLE_ARN`, `AWS_REGION`, `DOCS_SITE_URL` を設定する。
2. `.github/workflows/docs-deploy.yml` を `workflow_dispatch` で起動し、`execute_deploy=true` を指定する。
3. 実行ログで `aws sts get-caller-identity` が成功し、`task docs:deploy:ci` が完了することを確認する。
4. `execute_deploy=false` または `push(main)` では `task docs:guard` のみが実行されることを確認する。
5. `infra/` 未実装時は `infra:deploy:ci` が skeleton 動作（skip）となるため、infra 実装後に本番デプロイ処理へ置換する。

## 変更履歴
- 2026-03-13: `POST /runs/{run_id}/cancel` の運用手順と `CANCELLED` 完了判定を追加 [[RQ-FR-017]]
- 2026-03-01: 実行手順（CLI）とデバッグ手順（Logs/S3/DynamoDB 切り分け）を追記 [[DD-INF-DEP-002]]
- 2026-02-28: docs-deploy の配信手順（environment 変数/手動 deploy 条件）を追記 [[BD-SYS-ADR-001]]
- 2026-02-28: 非常時運用（常時開放しない）制約を反映 [[BD-SYS-ADR-001]]
- 2026-02-28: UC/NFR（可観測性）への追跡リンクを追加 [[BD-SYS-ADR-001]]
- 2026-02-28: 初版作成（plan.md の運用初期値と障害対応を Runbook 化） [[BD-SYS-ADR-001]]
