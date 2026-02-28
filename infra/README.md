# Infra Scaffold

This directory contains the AWS CDK implementation for the `/runs` control API.

## Included resources

- S3 bucket for run artifacts (`llm-temp-introspection-artifacts`)
- DynamoDB table for run status and idempotency (`run_control_table`)
- Lambda functions: `start_run`, `status`, `artifacts`, `orchestrator`
- Orchestrator alias (`live`) used as invoke target from `start_run`
- Bedrock Batch service role
- CloudWatch alarms for orchestrator failures and run health metrics
- Optional SNS alarm notifications (context `enable_notifications=true`)
- API Gateway routes:
  - `POST /runs`
  - `GET /runs/{run_id}`
  - `GET /runs/{run_id}/artifacts`

## Usage

```bash
uv sync --group infra
uv run --group infra --no-binary cdk synth

# enable SNS-backed alarms
uv run --group infra --no-binary cdk synth -c enable_notifications=true
```

`aws-cdk-lib` transitive packages occasionally publish wheels that fail uv metadata validation.
Using `--no-binary` makes uv build from sdist and avoids this issue reliably.
