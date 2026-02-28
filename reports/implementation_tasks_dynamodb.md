# implementation_tasks_dynamodb

## 目的
- `RunStatus/idempotency` を DynamoDB 正本、成果物本文を S3 正本とする実装へ移行する。
- Study1 MVP（`POST /runs` -> durable実行 -> `GET /runs/{run_id}` / `GET /runs/{run_id}/artifacts`）を最短で成立させる。

## 実装スコープ（MVP）
- API: `POST /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/artifacts`
- orchestration: Study1 enumerate/submit/poll/normalize
- state store: DynamoDB（run_control）
- artifacts store: S3（runs/{run_id}/...）

## パッチ単位タスク

### P1: Infra/CDK 土台作成
- 追加: `infra/README.md`
- 追加: `infra/app.py`
- 追加: `infra/requirements.txt`
- 追加: `infra/stacks/experiment_stack.py`
- 内容:
  - S3 bucket（artifacts）
  - DynamoDB table `run_control_table`（PK=`run_id`, GSI=`idempotency_key`）
  - Lambda `start_run_fn`, `orchestrator_fn`, `status_fn`
  - API Gateway routes（`/runs` 系）
  - IAM最小権限（S3 + DynamoDB + Bedrock + Logs + Metrics）

### P2: Lambda 共通モデル
- 追加: `app/common/models.py`
- 追加: `app/common/errors.py`
- 追加: `app/common/idempotency.py`
- 内容:
  - `RunCreateRequest`, `RunStatus`, `RunControl`
  - `request_hash` 生成
  - `record_id` 生成（sha256）

### P3: `POST /runs` 実装
- 追加: `app/start_run/handler.py`
- 追加: `app/start_run/repository.py`
- 内容:
  - 入力検証（`loops=10`, `full_cross=true`）
  - `idempotency_key` 同値再送判定
  - 同一条件: 既存 `run_id` を `202` 返却
  - 異条件: `409 Conflict`
  - 新規: S3 `config.json` 保存 + DynamoDB `QUEUED` 登録 + durable起動

### P4: `GET /runs/{run_id}` 実装
- 追加: `app/status/handler.py`
- 追加: `app/status/repository.py`
- 内容:
  - DynamoDB `RunStatus` 取得
  - `phase/state/progress/retry_count/last_error` を整形して返却
  - 未知 `run_id` は `404`

### P5: `GET /runs/{run_id}/artifacts` 実装
- 追加: `app/artifacts/handler.py`
- 内容:
  - S3 prefix (`reports/normalized/invalid`) 列挙
  - 200 + 配列（空配列可）
  - 署名URL返却は将来拡張（MVPはキー一覧）

### P6: Orchestrator Step（Study1）
- 追加: `app/orchestrator/handler.py`
- 追加: `app/orchestrator/steps/study1_enumerate.py`
- 追加: `app/orchestrator/steps/batch_submit.py`
- 追加: `app/orchestrator/steps/batch_poll.py`
- 追加: `app/orchestrator/steps/normalize.py`
- 内容:
  - step開始/完了ごとに DynamoDB 更新
  - shard失敗時1回retry、`retry_count` 反映
  - parse失敗は `invalid/` へ退避

### P7: レポート最小出力
- 追加: `app/report_builder/handler.py`
- 内容:
  - `study1_summary.csv`
  - `run_manifest.json`（phase_counts/retry_counts/invalid_counts）

### P8: テスト
- 追加: `tests/test_post_runs_idempotency.py`
- 追加: `tests/test_get_run_status.py`
- 追加: `tests/test_get_artifacts.py`
- 追加: `tests/test_record_id_deterministic.py`
- 内容:
  - 同一key同一条件=同一run_id
  - 同一key異条件=409
  - `GET /runs/{run_id}` がDynamoDB正本を返却

## 実装時の不変条件
- DynamoDBは制御情報のみ保持し、CSV/JSONL本文を保存しない。
- 実データDLはS3を正本とする。
- 書き込み順序は「S3成功 -> DynamoDB反映」を基本とする。

## 完了判定（MVP）
- `POST /runs` が `202` と `run_id` を返し、冪等/409分岐が動作する。
- `GET /runs/{run_id}` が DynamoDB 正本の状態を返す。
- `GET /runs/{run_id}/artifacts` で S3 キー一覧が返る。
- Study1 の最小成果物（`study1_summary.csv`, `run_manifest.json`）が S3 に出力される。
