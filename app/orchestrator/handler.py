import csv
import datetime
import hashlib
import io
import json
import logging
import os
import uuid
from collections import Counter

import boto3

from app.common.api import is_valid_run_id
from app.common.models import PredictionBatchRow, Study1BatchRow

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.client("dynamodb")
s3 = boto3.client("s3")
bedrock = boto3.client("bedrock")
lambda_client = boto3.client("lambda")
cloudwatch = boto3.client("cloudwatch")

TABLE_NAME = os.environ["TABLE_NAME"]
ARTIFACTS_BUCKET = os.environ["ARTIFACTS_BUCKET"]
BEDROCK_BATCH_ROLE_ARN = os.environ.get("BEDROCK_BATCH_ROLE_ARN")
SELF_ARN = os.environ.get("SELF_ARN", "")
METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", "ReflectBench/Run")

DEFAULT_POLL_INTERVAL_SEC = int(os.environ.get("DEFAULT_POLL_INTERVAL_SEC", "180"))
BATCH_POLL_MAX_ATTEMPTS = int(os.environ.get("BATCH_POLL_MAX_ATTEMPTS", "20"))
BATCH_DRY_RUN = os.environ.get("BATCH_DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}
LEASE_SECONDS = int(os.environ.get("LEASE_SECONDS", "300"))
MAX_PHASES_PER_INVOCATION = int(os.environ.get("MAX_PHASES_PER_INVOCATION", "1"))

PHASES = [
    "STUDY1_ENUMERATE",
    "STUDY1_BATCH_SUBMIT",
    "STUDY1_BATCH_POLL",
    "STUDY1_NORMALIZE",
    "STUDY2_PREPARE",
    "STUDY2_WITHIN",
    "STUDY2_ACROSS",
    "EXPERIMENT_A",
    "EXPERIMENT_D",
    "REPORT",
]

PROMPT_TYPES = ["FACTUAL", "NORMAL", "CRAZY"]
TARGETS = ["像", "ゾウ", "ユニコーン", "マーロック", "アイレット・ドコドコ・ヤッタゼ・ペンギン"]


class PipelineError(Exception):
    def __init__(self, *, step: str, reason: str, retryable: bool, category: str) -> None:
        super().__init__(reason)
        self.step = step
        self.reason = reason
        self.retryable = retryable
        self.category = category


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record_id(
    *,
    run_id: str,
    phase: str,
    model: str,
    target: str,
    prompt_type: str,
    temperature: float,
    loop_index: int,
) -> str:
    base = "|".join(
        [run_id, phase, model, target, prompt_type, f"{temperature:.1f}", str(loop_index)]
    )
    return _sha256(base)


def _log(level: str, payload: dict) -> None:
    message = json.dumps(payload, ensure_ascii=False)
    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)


def _put_metric_data(run_id: str, metric_data: list[dict]) -> None:
    dimensions = [{"Name": "RunId", "Value": run_id}]
    payload: list[dict] = []
    for item in metric_data:
        payload.append(
            {
                "MetricName": item["MetricName"],
                "Unit": item.get("Unit", "Count"),
                "Value": float(item["Value"]),
                "Dimensions": dimensions,
            }
        )
    cloudwatch.put_metric_data(Namespace=METRIC_NAMESPACE, MetricData=payload)


def _parse_iso_or_none(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


def _run_duration_sec(run_id: str) -> float:
    item = _get_run_item(run_id)
    started = _parse_iso_or_none(item.get("started_at", {}).get("S"))
    if started is None:
        started = _parse_iso_or_none(item.get("created_at", {}).get("S"))
    finished = _parse_iso_or_none(item.get("finished_at", {}).get("S"))
    if started is None:
        return 0.0
    if finished is None:
        finished = _now()
    delta = (finished - started).total_seconds()
    return max(delta, 0.0)


def _sum_shard_retries(run_id: str) -> int:
    keys = [key for key in _s3_list(f"runs/{run_id}/batch-output/") if key.endswith("-job.json")]
    retries = 0
    for key in keys:
        try:
            payload = _s3_get_json(key)
            attempts = int(payload.get("attempts", 1))
        except Exception:  # noqa: BLE001
            continue
        retries += max(attempts - 1, 0)
    return retries


def _sum_parse_failures(state: dict) -> int:
    return sum(int(value) for value in state.get("invalid_counts", {}).values())


def _emit_finalize_metrics(run_id: str, final_state: str, state: dict) -> None:
    metric_data = [
        {"MetricName": "RunDurationSec", "Unit": "Seconds", "Value": _run_duration_sec(run_id)},
        {"MetricName": "ParseFailureCount", "Unit": "Count", "Value": _sum_parse_failures(state)},
        {"MetricName": "ShardRetryCount", "Unit": "Count", "Value": _sum_shard_retries(run_id)},
    ]
    if final_state == "SUCCEEDED":
        metric_data.append({"MetricName": "RunSucceeded", "Unit": "Count", "Value": 1})
    else:
        metric_data.append({"MetricName": "RunFailed", "Unit": "Count", "Value": 1})

    try:
        _put_metric_data(run_id, metric_data)
    except Exception as exc:  # noqa: BLE001
        _log(
            "warning",
            {
                "run_id": run_id,
                "step": "METRICS",
                "message": f"failed to publish metrics: {exc}",
            },
        )


def _s3_put_json(key: str, payload: dict) -> None:
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def _s3_put_jsonl(key: str, rows: list[dict]) -> None:
    body = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/jsonl",
    )


def _s3_get_json(key: str) -> dict:
    res = s3.get_object(Bucket=ARTIFACTS_BUCKET, Key=key)
    return json.loads(res["Body"].read().decode("utf-8"))


def _s3_get_jsonl(key: str) -> list[dict]:
    res = s3.get_object(Bucket=ARTIFACTS_BUCKET, Key=key)
    raw = res["Body"].read().decode("utf-8")
    rows: list[dict] = []
    for idx, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(parsed)
        except json.JSONDecodeError as exc:
            raise PipelineError(
                step="JSONL_PARSE",
                reason=f"{key}:{idx} is not strict JSON object: {exc}",
                retryable=False,
                category="validation",
            ) from exc
    return rows


def _s3_list(prefix: str) -> list[str]:
    keys: list[str] = []
    token: str | None = None
    while True:
        kwargs: dict = {"Bucket": ARTIFACTS_BUCKET, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        res = s3.list_objects_v2(**kwargs)
        for obj in res.get("Contents", []):
            keys.append(obj["Key"])
        if not res.get("IsTruncated"):
            break
        token = res.get("NextContinuationToken")
    return sorted(keys)


def _get_run_item(run_id: str) -> dict:
    res = dynamodb.get_item(
        TableName=TABLE_NAME, Key={"run_id": {"S": run_id}}, ConsistentRead=True
    )
    item = res.get("Item")
    if not item:
        raise PipelineError(
            step="LOAD_RUN",
            reason="run_id not found",
            retryable=False,
            category="validation",
        )
    return item


def _load_state(run_id: str) -> dict:
    item = _get_run_item(run_id)
    raw = item.get("orchestration_state", {}).get("S")
    if not raw:
        return {"cursor": 0, "phase_counts": {}, "invalid_counts": {}, "retry_count": 0}
    state = json.loads(raw)
    state.setdefault("cursor", 0)
    state.setdefault("phase_counts", {})
    state.setdefault("invalid_counts", {})
    state.setdefault("retry_count", 0)
    return state


def _save_state(run_id: str, state: dict) -> None:
    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": run_id}},
        UpdateExpression="SET orchestration_state = :s, updated_at = :u",
        ExpressionAttributeValues={
            ":s": {"S": json.dumps(state, ensure_ascii=False)},
            ":u": {"S": _now_iso()},
        },
    )


def _acquire_lease(run_id: str, owner: str) -> bool:
    now = int(_now().timestamp())
    lease_until = now + LEASE_SECONDS
    try:
        dynamodb.update_item(
            TableName=TABLE_NAME,
            Key={"run_id": {"S": run_id}},
            UpdateExpression="SET lease_owner = :owner, lease_until = :lease_until",
            ConditionExpression=(
                "attribute_not_exists(lease_until) OR lease_until < :now OR lease_owner = :owner"
            ),
            ExpressionAttributeValues={
                ":owner": {"S": owner},
                ":lease_until": {"N": str(lease_until)},
                ":now": {"N": str(now)},
            },
        )
        return True
    except dynamodb.exceptions.ConditionalCheckFailedException:
        return False


def _release_lease(run_id: str, owner: str) -> None:
    try:
        dynamodb.update_item(
            TableName=TABLE_NAME,
            Key={"run_id": {"S": run_id}},
            UpdateExpression="REMOVE lease_owner, lease_until",
            ConditionExpression="lease_owner = :owner",
            ExpressionAttributeValues={":owner": {"S": owner}},
        )
    except dynamodb.exceptions.ConditionalCheckFailedException:
        return


def _update_status(
    run_id: str,
    *,
    phase: str,
    state: str,
    completed: int,
    retry_count: int,
    trace_id: str,
    step: str,
    last_error: dict | None = None,
) -> None:
    percent = int((completed / len(PHASES)) * 100)
    now = _now_iso()

    expr = (
        "SET phase = :phase, #state = :state, progress = :progress, retry_count = :retry_count, "
        "updated_at = :updated_at, started_at = if_not_exists(started_at, :updated_at)"
    )
    values: dict = {
        ":phase": {"S": phase},
        ":state": {"S": state},
        ":progress": {
            "M": {
                "completed_steps": {"N": str(completed)},
                "total_steps": {"N": str(len(PHASES))},
                "percent": {"N": str(percent)},
            }
        },
        ":retry_count": {"N": str(retry_count)},
        ":updated_at": {"S": now},
    }

    if last_error is not None:
        expr += ", last_error = :last_error"
        values[":last_error"] = {
            "M": {
                "step": {"S": str(last_error.get("step", step))},
                "reason": {"S": str(last_error.get("reason", "unknown"))[:500]},
                "retryable": {"BOOL": bool(last_error.get("retryable", False))},
                "category": {"S": str(last_error.get("category", "internal"))},
                "trace_id": {"S": trace_id},
            }
        }

    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": run_id}},
        UpdateExpression=expr,
        ExpressionAttributeNames={"#state": "state"},
        ExpressionAttributeValues=values,
    )


def _finalize(
    run_id: str, state: str, retry_count: int, trace_id: str, last_error: dict | None = None
) -> None:
    expr = (
        "SET phase = :phase, #state = :state, finished_at = :finished_at, updated_at = :updated_at"
    )
    values: dict = {
        ":phase": {"S": "REPORT"},
        ":state": {"S": state},
        ":finished_at": {"S": _now_iso()},
        ":updated_at": {"S": _now_iso()},
    }
    if last_error is not None:
        expr += ", last_error = :last_error"
        values[":last_error"] = {
            "M": {
                "step": {"S": str(last_error.get("step", "ORCHESTRATOR"))},
                "reason": {"S": str(last_error.get("reason", "unknown"))[:500]},
                "retryable": {"BOOL": bool(last_error.get("retryable", False))},
                "category": {"S": str(last_error.get("category", "internal"))},
                "trace_id": {"S": trace_id},
            }
        }
    expr += ", retry_count = :retry_count"
    values[":retry_count"] = {"N": str(retry_count)}

    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={"run_id": {"S": run_id}},
        UpdateExpression=expr,
        ExpressionAttributeNames={"#state": "state"},
        ExpressionAttributeValues=values,
    )


def _load_config(run_id: str) -> dict:
    return _s3_get_json(f"runs/{run_id}/config.json")


def _encode_model_key(model_id: str) -> str:
    return model_id.replace(":", "__COLON__")


def _decode_model_key(model_key: str) -> str:
    return model_key.replace("__COLON__", ":")


def _model_id_from_manifest_key(manifest_key: str, phase: str) -> str:
    parts = manifest_key.split("/")
    if len(parts) >= 6 and parts[2] == "manifests":
        return _decode_model_key(parts[4])

    rows = _s3_get_jsonl(manifest_key)
    if not rows:
        raise PipelineError(
            step=f"{phase.upper()}_BATCH_SUBMIT",
            reason=f"manifest is empty: {manifest_key}",
            retryable=False,
            category="validation",
        )

    first = rows[0]
    for key in ("predictor_model", "model_id", "generator_model"):
        if first.get(key):
            return str(first[key])

    raise PipelineError(
        step=f"{phase.upper()}_BATCH_SUBMIT",
        reason=f"failed to infer model_id from manifest: {manifest_key}",
        retryable=False,
        category="validation",
    )


def _to_s3_uri(key: str) -> str:
    return f"s3://{ARTIFACTS_BUCKET}/{key}"


def _metadata_key_for_manifest(manifest_key: str, phase: str) -> str:
    return manifest_key.replace(f"/manifests/{phase}/", f"/batch-output/{phase}/").replace(
        ".jsonl", "-job.json"
    )


def _output_key_for_manifest(manifest_key: str, phase: str) -> str:
    return manifest_key.replace(f"/manifests/{phase}/", f"/batch-output/{phase}/")


def _submit_batch_jobs(run_id: str, phase: str) -> dict[str, str]:
    manifest_keys = [
        key for key in _s3_list(f"runs/{run_id}/manifests/{phase}/") if key.endswith(".jsonl")
    ]
    jobs: dict[str, str] = {}
    for key in manifest_keys:
        metadata_key = _metadata_key_for_manifest(key, phase)
        output_key = _output_key_for_manifest(key, phase)
        model_id = _model_id_from_manifest_key(key, phase)

        if BATCH_DRY_RUN:
            job_identifier = f"dryrun-{_sha256(key)[:24]}"
            jobs[key] = job_identifier
            _s3_put_json(
                metadata_key,
                {
                    "job_identifier": job_identifier,
                    "status": "COMPLETED",
                    "manifest_key": key,
                    "output_key": output_key,
                    "submitted_at": _now_iso(),
                    "completed_at": _now_iso(),
                    "attempts": 1,
                    "dry_run": True,
                },
            )
            continue

        if not BEDROCK_BATCH_ROLE_ARN:
            raise PipelineError(
                step=f"{phase.upper()}_BATCH_SUBMIT",
                reason="BEDROCK_BATCH_ROLE_ARN is required when BATCH_DRY_RUN=false",
                retryable=False,
                category="validation",
            )

        output_prefix = key.replace(f"/manifests/{phase}/", f"/batch-output/{phase}/").replace(
            ".jsonl", "/"
        )

        attempts = 0
        while attempts < 2:
            attempts += 1
            job_name = f"rb-{phase}-{_sha256(f'{key}|{attempts}')[:24]}"
            try:
                response = bedrock.create_model_invocation_job(
                    jobName=job_name,
                    roleArn=BEDROCK_BATCH_ROLE_ARN,
                    modelId=model_id,
                    inputDataConfig={"s3InputDataConfig": {"s3Uri": _to_s3_uri(key)}},
                    outputDataConfig={"s3OutputDataConfig": {"s3Uri": _to_s3_uri(output_prefix)}},
                )
                job_identifier = str(
                    response.get("jobArn") or response.get("jobIdentifier") or job_name
                )
                jobs[key] = job_identifier
                _s3_put_json(
                    metadata_key,
                    {
                        "job_identifier": job_identifier,
                        "status": "SUBMITTED",
                        "manifest_key": key,
                        "output_key": output_key,
                        "model_id": model_id,
                        "submitted_at": _now_iso(),
                        "attempts": attempts,
                        "dry_run": False,
                    },
                )
                break
            except Exception as exc:  # noqa: BLE001
                if attempts >= 2:
                    raise PipelineError(
                        step=f"{phase.upper()}_BATCH_SUBMIT",
                        reason=f"failed to submit batch job for {key}: {exc}",
                        retryable=True,
                        category="dependency",
                    ) from exc
    return jobs


def _load_jobs_from_metadata(run_id: str, phase: str) -> dict[str, str]:
    metadata_keys = [
        key for key in _s3_list(f"runs/{run_id}/batch-output/{phase}/") if key.endswith("-job.json")
    ]
    jobs: dict[str, str] = {}
    for key in metadata_keys:
        meta = _s3_get_json(key)
        manifest_key = str(meta.get("manifest_key", ""))
        job_identifier = str(meta.get("job_identifier", ""))
        if manifest_key and job_identifier:
            jobs[manifest_key] = job_identifier
    return jobs


def _poll_batch_jobs(
    run_id: str, phase: str, jobs: dict[str, str], _poll_interval_sec: int
) -> bool:
    if not jobs or BATCH_DRY_RUN:
        return True

    has_pending = False
    for manifest_key, job_identifier in jobs.items():
        metadata_key = _metadata_key_for_manifest(manifest_key, phase)
        try:
            res = bedrock.get_model_invocation_job(jobIdentifier=job_identifier)
            status = str(res.get("status", "UNKNOWN"))
        except Exception as exc:  # noqa: BLE001
            raise PipelineError(
                step=f"{phase.upper()}_BATCH_POLL",
                reason=f"failed to poll job {job_identifier}: {exc}",
                retryable=True,
                category="dependency",
            ) from exc

        if status in {"Completed", "COMPLETED"}:
            _s3_put_json(
                metadata_key,
                {
                    "job_identifier": job_identifier,
                    "status": "COMPLETED",
                    "manifest_key": manifest_key,
                    "output_key": _output_key_for_manifest(manifest_key, phase),
                    "completed_at": _now_iso(),
                    "dry_run": False,
                },
            )
            continue

        if status in {"Failed", "FAILED", "Stopped", "STOPPED"}:
            raise PipelineError(
                step=f"{phase.upper()}_BATCH_POLL",
                reason=f"job {job_identifier} ended with status={status}",
                retryable=True,
                category="dependency",
            )

        has_pending = True

    return not has_pending


def _materialize_dryrun_batch_output_for_phase(run_id: str, phase: str) -> None:
    if not BATCH_DRY_RUN:
        return

    manifest_keys = [
        key for key in _s3_list(f"runs/{run_id}/manifests/{phase}/") if key.endswith(".jsonl")
    ]
    for manifest_key in manifest_keys:
        rows = _s3_get_jsonl(manifest_key)
        out_rows: list[dict] = []
        for row in rows:
            if phase == "study1":
                temp = float(row["temperature"])
                judgment = "HIGH" if temp >= 0.5 else "LOW"
                out_rows.append(
                    {
                        "record_id": row["record_id"],
                        "run_id": run_id,
                        "phase": "study1",
                        "model_id": row["model_id"],
                        "temperature": temp,
                        "prompt_type": row["prompt_type"],
                        "target": row["target"],
                        "loop_index": row["loop_index"],
                        "generated_sentence": (
                            f"{row['target']}について{row['prompt_type']}な文。temperature={temp:.1f}"
                        ),
                        "reasoning": "deterministic baseline",
                        "judgment": judgment,
                    }
                )
                continue

            expected = str(row.get("expected_label", "HIGH"))
            seed = (
                f"{phase}|{row.get('condition_type')}|{row.get('source_record_id')}"
                f"|{row.get('predictor_model')}"
            )
            predicted = _predict_label(seed, expected)
            out_rows.append(
                {
                    "source_record_id": row.get("source_record_id"),
                    "generator_model": row.get("generator_model"),
                    "predictor_model": row.get("predictor_model"),
                    "expected_label": expected,
                    "condition_type": row.get("condition_type"),
                    "predicted_label": predicted,
                }
            )

        _s3_put_jsonl(_output_key_for_manifest(manifest_key, phase), out_rows)


def _write_invalid_rows(run_id: str, phase: str, rows: list[dict]) -> None:
    if not rows:
        return
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        model = str(row.get("model", "unknown"))
        grouped.setdefault(model, []).append(row)

    for model, model_rows in grouped.items():
        key = f"runs/{run_id}/invalid/{phase}/{model}/invalid.jsonl"
        _s3_put_jsonl(key, model_rows)


def _normalize_study1(run_id: str) -> tuple[list[dict], list[dict]]:
    normalized: list[dict] = []
    invalid_rows: list[dict] = []
    output_keys = [
        key
        for key in _s3_list(f"runs/{run_id}/batch-output/study1/")
        if key.endswith(".jsonl") and not key.endswith("-job.json")
    ]

    for key in output_keys:
        rows = _s3_get_jsonl(key)
        out_rows: list[dict] = []
        for row in rows:
            try:
                parsed = Study1BatchRow.model_validate(row)
            except Exception as exc:  # noqa: BLE001
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": "study1",
                        "record_id": str(row.get("record_id", "unknown")),
                        "model": str(row.get("model_id", "unknown")),
                        "reason": f"schema validation failed: {exc}",
                        "raw_text": json.dumps(row, ensure_ascii=False),
                    }
                )
                continue

            rec = parsed.model_dump()
            out_rows.append(rec)
            normalized.append(rec)

        out_key = key.replace("/batch-output/study1/", "/normalized/study1/")
        _s3_put_jsonl(out_key, out_rows)

    _write_invalid_rows(run_id, "study1", invalid_rows)
    return normalized, invalid_rows


def _expected_label(temp: float, low_max: float, high_min: float) -> str | None:
    if temp <= low_max:
        return "LOW"
    if temp >= high_min:
        return "HIGH"
    return None


def _write_sharded(prefix: str, rows: list[dict], shard_size: int) -> int:
    part = 1
    written = 0
    chunk: list[dict] = []
    for row in rows:
        chunk.append(row)
        if len(chunk) == shard_size:
            _s3_put_jsonl(f"{prefix}/part-{part:05d}.jsonl", chunk)
            written += len(chunk)
            chunk = []
            part += 1
    if chunk:
        _s3_put_jsonl(f"{prefix}/part-{part:05d}.jsonl", chunk)
        written += len(chunk)
    return written


def _prepare_downstream_manifests(run_id: str, rows: list[dict], config: dict) -> dict[str, int]:
    models = list(config.get("models", []))
    shard_size = int(config.get("shard_size", 500))

    study2_candidates = []
    ad_candidates = []
    for row in rows:
        temp = float(row["temperature"])
        label_study2 = _expected_label(temp, 0.2, 0.8)
        if label_study2 is not None:
            study2_candidates.append((row, label_study2))
        label_ad = _expected_label(temp, 0.5, 0.8)
        if label_ad is not None:
            ad_candidates.append((row, label_ad))

    within_rows = [
        {
            "source_record_id": row["record_id"],
            "generator_model": row["model_id"],
            "predictor_model": row["model_id"],
            "prompt_type": row["prompt_type"],
            "target": row["target"],
            "temperature": row["temperature"],
            "expected_label": label,
            "condition_type": "within",
        }
        for row, label in study2_candidates
    ]

    across_rows: list[dict] = []
    for row, label in study2_candidates:
        for predictor in models:
            if predictor == row["model_id"]:
                continue
            across_rows.append(
                {
                    "source_record_id": row["record_id"],
                    "generator_model": row["model_id"],
                    "predictor_model": predictor,
                    "prompt_type": row["prompt_type"],
                    "target": row["target"],
                    "temperature": row["temperature"],
                    "expected_label": label,
                    "condition_type": "across",
                }
            )

    exp_a_edit_rows = [
        {
            "source_record_id": row["record_id"],
            "generator_model": row["model_id"],
            "predictor_model": row["model_id"],
            "prompt_type": row["prompt_type"],
            "target": row["target"],
            "temperature": row["temperature"],
            "expected_label": label,
            "condition_type": "edit",
        }
        for row, label in ad_candidates
        if row["prompt_type"] == "NORMAL"
    ]

    exp_d_blind_rows = [
        {
            "source_record_id": row["record_id"],
            "generator_model": row["model_id"],
            "predictor_model": row["model_id"],
            "prompt_type": row["prompt_type"],
            "target": row["target"],
            "temperature": row["temperature"],
            "expected_label": label,
            "condition_type": "blind",
        }
        for row, label in ad_candidates
    ]

    exp_d_wrong_rows = [
        {
            "source_record_id": row["record_id"],
            "generator_model": row["model_id"],
            "predictor_model": row["model_id"],
            "prompt_type": row["prompt_type"],
            "target": row["target"],
            "temperature": row["temperature"],
            "expected_label": label,
            "condition_type": "wrong_label",
        }
        for row, label in ad_candidates
        if row["prompt_type"] in {"FACTUAL", "CRAZY"}
    ]

    return {
        "study2_within": _write_sharded(
            f"runs/{run_id}/manifests/study2_within", within_rows, shard_size
        ),
        "study2_across": _write_sharded(
            f"runs/{run_id}/manifests/study2_across", across_rows, shard_size
        ),
        "experiment_a_edit": _write_sharded(
            f"runs/{run_id}/manifests/experiment_a_edit", exp_a_edit_rows, shard_size
        ),
        "experiment_d_blind": _write_sharded(
            f"runs/{run_id}/manifests/experiment_d_blind", exp_d_blind_rows, shard_size
        ),
        "experiment_d_wrong_label": _write_sharded(
            f"runs/{run_id}/manifests/experiment_d_wrong_label", exp_d_wrong_rows, shard_size
        ),
    }


def _predict_label(seed: str, expected: str) -> str:
    if int(_sha256(seed), 16) % 10 < 7:
        return expected
    return "LOW" if expected == "HIGH" else "HIGH"


def _run_prediction_phase(run_id: str, phase: str) -> tuple[list[dict], list[dict]]:
    output_keys = [
        key
        for key in _s3_list(f"runs/{run_id}/batch-output/{phase}/")
        if key.endswith(".jsonl") and not key.endswith("-job.json")
    ]

    output_rows: list[dict] = []
    invalid_rows: list[dict] = []
    for key in output_keys:
        rows = _s3_get_jsonl(key)
        normalized_rows: list[dict] = []
        for row in rows:
            try:
                parsed = PredictionBatchRow.model_validate(row)
            except Exception as exc:  # noqa: BLE001
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": phase,
                        "record_id": str(row.get("source_record_id", "unknown")),
                        "model": str(row.get("predictor_model", "unknown")),
                        "reason": f"schema validation failed: {exc}",
                        "raw_text": json.dumps(row, ensure_ascii=False),
                    }
                )
                continue

            validated = parsed.model_dump()
            seed = (
                f"{phase}|{validated['source_record_id']}|{validated['predictor_model']}"
                f"|{validated['condition_type']}"
            )
            result = {
                "record_id": _sha256(seed),
                "run_id": run_id,
                "phase": phase,
                "condition_type": validated["condition_type"],
                "generator_model": validated["generator_model"],
                "predictor_model": validated["predictor_model"],
                "source_record_id": validated["source_record_id"],
                "expected_label": validated["expected_label"],
                "predicted_label": validated["predicted_label"],
                "is_correct": validated["predicted_label"] == validated["expected_label"],
                "raw_text": json.dumps(validated, ensure_ascii=False),
            }
            normalized_rows.append(result)
            output_rows.append(result)

        out_key = key.replace(f"/batch-output/{phase}/", f"/normalized/{phase}/")
        _s3_put_jsonl(out_key, normalized_rows)

    _write_invalid_rows(run_id, phase, invalid_rows)
    return output_rows, invalid_rows


def _write_prediction_manifests(
    run_id: str,
    phase: str,
    base_rows: list[dict],
    models: list[str],
    shard_size: int,
    *,
    condition_types: list[str] | None = None,
) -> int:
    manifest_rows: list[dict] = []
    for row in base_rows:
        if row.get("expected_label") not in {"HIGH", "LOW"}:
            continue
        for predictor in models:
            if condition_types is None:
                condition = row.get("condition_type")
                if not condition:
                    continue
                condition_set: list[str] = [str(condition)]
            else:
                condition_set = list(condition_types)
            for condition_type in condition_set:
                manifest_rows.append(
                    {
                        "source_record_id": row["source_record_id"],
                        "generator_model": row["generator_model"],
                        "predictor_model": predictor,
                        "expected_label": row["expected_label"],
                        "condition_type": condition_type,
                    }
                )
    return _write_sharded(f"runs/{run_id}/manifests/{phase}", manifest_rows, shard_size)


def _run_experiment_a(
    run_id: str,
    models: list[str],
    shard_size: int,
    poll_interval_sec: int,
) -> tuple[list[dict], list[dict]] | None:
    edit_keys = [
        key
        for key in _s3_list(f"runs/{run_id}/manifests/experiment_a_edit/")
        if key.endswith(".jsonl")
    ]
    edited_rows: list[dict] = []
    invalid_rows: list[dict] = []

    for key in edit_keys:
        rows = _s3_get_jsonl(key)
        out_rows: list[dict] = []
        for row in rows:
            if row.get("expected_label") not in {"HIGH", "LOW"}:
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": "experiment_a",
                        "record_id": str(row.get("source_record_id", "unknown")),
                        "model": str(row.get("generator_model", "unknown")),
                        "reason": "expected_label must be HIGH or LOW",
                        "raw_text": json.dumps(row, ensure_ascii=False),
                    }
                )
                continue
            edited = {
                **row,
                "info_plus": f"{row['target']}の詳細情報を追加した文",
                "info_minus": f"{row['target']}の要点だけを残した文",
            }
            out_rows.append(edited)
            edited_rows.append(edited)
        out_key = key.replace("/manifests/experiment_a_edit/", "/normalized/experiment_a_edit/")
        _s3_put_jsonl(out_key, out_rows)

    _write_prediction_manifests(
        run_id,
        "experiment_a_predict",
        edited_rows,
        models,
        shard_size,
        condition_types=["info_plus", "info_minus"],
    )
    jobs = _load_jobs_from_metadata(run_id, "experiment_a_predict")
    if not jobs:
        jobs = _submit_batch_jobs(run_id, "experiment_a_predict")
    if not _poll_batch_jobs(run_id, "experiment_a_predict", jobs, poll_interval_sec):
        return None
    _materialize_dryrun_batch_output_for_phase(run_id, "experiment_a_predict")
    predictions, pred_invalid = _run_prediction_phase(run_id, "experiment_a_predict")
    for row in predictions:
        row["phase"] = "experiment_a"

    all_invalid = invalid_rows + pred_invalid
    if predictions:
        _s3_put_jsonl(f"runs/{run_id}/normalized/experiment_a/results.jsonl", predictions)
    _write_invalid_rows(run_id, "experiment_a", all_invalid)
    return predictions, all_invalid


def _run_experiment_d(
    run_id: str,
    models: list[str],
    shard_size: int,
    poll_interval_sec: int,
) -> tuple[list[dict], list[dict]] | None:
    base_rows: list[dict] = []
    invalid_rows: list[dict] = []
    blind_keys = [
        key
        for key in _s3_list(f"runs/{run_id}/manifests/experiment_d_blind/")
        if key.endswith(".jsonl")
    ]
    for key in blind_keys:
        rows = _s3_get_jsonl(key)
        for row in rows:
            if row.get("expected_label") not in {"HIGH", "LOW"}:
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": "experiment_d",
                        "record_id": str(row.get("source_record_id", "unknown")),
                        "model": str(row.get("generator_model", "unknown")),
                        "reason": "expected_label must be HIGH or LOW",
                        "raw_text": json.dumps(row, ensure_ascii=False),
                    }
                )
                continue
            base_rows.append({**row, "condition_type": "blind"})

    wrong_keys = [
        key
        for key in _s3_list(f"runs/{run_id}/manifests/experiment_d_wrong_label/")
        if key.endswith(".jsonl")
    ]
    for key in wrong_keys:
        rows = _s3_get_jsonl(key)
        for row in rows:
            if row.get("expected_label") not in {"HIGH", "LOW"}:
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": "experiment_d",
                        "record_id": str(row.get("source_record_id", "unknown")),
                        "model": str(row.get("generator_model", "unknown")),
                        "reason": "expected_label must be HIGH or LOW",
                        "raw_text": json.dumps(row, ensure_ascii=False),
                    }
                )
                continue
            base_rows.append({**row, "condition_type": "wrong_label"})

    _write_prediction_manifests(run_id, "experiment_d_predict", base_rows, models, shard_size)
    jobs = _load_jobs_from_metadata(run_id, "experiment_d_predict")
    if not jobs:
        jobs = _submit_batch_jobs(run_id, "experiment_d_predict")
    if not _poll_batch_jobs(run_id, "experiment_d_predict", jobs, poll_interval_sec):
        return None
    _materialize_dryrun_batch_output_for_phase(run_id, "experiment_d_predict")
    results, pred_invalid = _run_prediction_phase(run_id, "experiment_d_predict")
    for row in results:
        row["phase"] = "experiment_d"

    all_invalid = invalid_rows + pred_invalid
    if results:
        _s3_put_jsonl(f"runs/{run_id}/normalized/experiment_d/results.jsonl", results)
    _write_invalid_rows(run_id, "experiment_d", all_invalid)
    return results, all_invalid


def _rows_to_csv(rows: list[dict], headers: list[str]) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({header: row.get(header) for header in headers})
    return out.getvalue().encode("utf-8")


def _load_normalized_rows(run_id: str, phase: str) -> list[dict]:
    keys = [
        key
        for key in _s3_list(f"runs/{run_id}/normalized/{phase}/")
        if key.endswith(".jsonl") and not key.endswith("-job.json")
    ]
    rows: list[dict] = []
    for key in keys:
        rows.extend(_s3_get_jsonl(key))
    return rows


def _write_reports(
    run_id: str, phase_counts: dict[str, int], invalid_counts: dict[str, int]
) -> None:
    study1_rows = _load_normalized_rows(run_id, "study1")
    within_rows = _load_normalized_rows(run_id, "study2_within")
    across_rows = _load_normalized_rows(run_id, "study2_across")
    experiment_a_rows = _load_normalized_rows(run_id, "experiment_a")
    experiment_d_rows = _load_normalized_rows(run_id, "experiment_d")

    model_counter = Counter(row["model_id"] for row in study1_rows if "model_id" in row)
    study1_summary = [
        {"model_id": model, "count": count} for model, count in sorted(model_counter.items())
    ]
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=f"runs/{run_id}/reports/study1_summary.csv",
        Body=_rows_to_csv(study1_summary, ["model_id", "count"]),
        ContentType="text/csv",
    )

    headers = [
        "generator_model",
        "predictor_model",
        "expected_label",
        "predicted_label",
        "is_correct",
    ]
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=f"runs/{run_id}/reports/study2_within.csv",
        Body=_rows_to_csv(within_rows, headers),
        ContentType="text/csv",
    )
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=f"runs/{run_id}/reports/study2_across.csv",
        Body=_rows_to_csv(across_rows, headers),
        ContentType="text/csv",
    )
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=f"runs/{run_id}/reports/experiment_a.csv",
        Body=_rows_to_csv(experiment_a_rows, ["condition_type", *headers]),
        ContentType="text/csv",
    )
    s3.put_object(
        Bucket=ARTIFACTS_BUCKET,
        Key=f"runs/{run_id}/reports/experiment_d.csv",
        Body=_rows_to_csv(experiment_d_rows, ["condition_type", *headers]),
        ContentType="text/csv",
    )

    _s3_put_json(
        f"runs/{run_id}/reports/run_manifest.json",
        {
            "run_id": run_id,
            "phase_counts": phase_counts,
            "retry_counts": {
                "study1": 0,
                "study2_within": 0,
                "study2_across": 0,
                "experiment_a": 0,
                "experiment_d": 0,
            },
            "invalid_counts": invalid_counts,
            "excluded_reasons": {},
            "estimated_model_cost_usd": 2.66,
        },
    )


def _generate_study1_manifests(run_id: str, config: dict) -> int:
    shard_size = int(config.get("shard_size", 500))
    loops = int(config.get("loops", 10))
    models = list(config.get("models", []))
    temperatures = [round(i * 0.1, 1) for i in range(11)]

    total = 0
    for model in models:
        model_key = _encode_model_key(model)
        part = 1
        rows: list[dict] = []
        for temperature in temperatures:
            for prompt_type in PROMPT_TYPES:
                for target in TARGETS:
                    for loop_index in range(loops):
                        rows.append(
                            {
                                "record_id": _record_id(
                                    run_id=run_id,
                                    phase="study1",
                                    model=model,
                                    target=target,
                                    prompt_type=prompt_type,
                                    temperature=temperature,
                                    loop_index=loop_index,
                                ),
                                "run_id": run_id,
                                "phase": "study1",
                                "model_id": model,
                                "temperature": temperature,
                                "prompt_type": prompt_type,
                                "target": target,
                                "loop_index": loop_index,
                            }
                        )
                        if len(rows) == shard_size:
                            key = (
                                f"runs/{run_id}/manifests/study1/{model_key}/part-{part:05d}.jsonl"
                            )
                            _s3_put_jsonl(key, rows)
                            total += len(rows)
                            rows = []
                            part += 1
        if rows:
            key = f"runs/{run_id}/manifests/study1/{model_key}/part-{part:05d}.jsonl"
            _s3_put_jsonl(key, rows)
            total += len(rows)
    return total


def _invoke_self(run_id: str, trace_id: str) -> None:
    if not SELF_ARN:
        return
    lambda_client.invoke(
        FunctionName=SELF_ARN,
        InvocationType="Event",
        Payload=json.dumps({"run_id": run_id, "trace_id": trace_id}).encode("utf-8"),
    )


def _execute_phase(run_id: str, state: dict, trace_id: str) -> dict:
    cursor = int(state.get("cursor", 0))
    phase = PHASES[cursor]
    config = _load_config(run_id)
    models = list(config.get("models", []))
    poll_interval_sec = int(config.get("poll_interval_sec", DEFAULT_POLL_INTERVAL_SEC))
    shard_size = int(config.get("shard_size", 500))

    _update_status(
        run_id,
        phase=phase,
        state="RUNNING",
        completed=cursor + 1,
        retry_count=int(state.get("retry_count", 0)),
        trace_id=trace_id,
        step=phase,
    )

    if phase == "STUDY1_ENUMERATE":
        state["phase_counts"]["study1"] = _generate_study1_manifests(run_id, config)
    elif phase == "STUDY1_BATCH_SUBMIT":
        _submit_batch_jobs(run_id, "study1")
    elif phase == "STUDY1_BATCH_POLL":
        jobs = _load_jobs_from_metadata(run_id, "study1")
        if not jobs:
            jobs = _submit_batch_jobs(run_id, "study1")
        if not _poll_batch_jobs(run_id, "study1", jobs, poll_interval_sec):
            return state
        _materialize_dryrun_batch_output_for_phase(run_id, "study1")
    elif phase == "STUDY1_NORMALIZE":
        _, invalid_rows = _normalize_study1(run_id)
        state["invalid_counts"]["study1"] = len(invalid_rows)
    elif phase == "STUDY2_PREPARE":
        study1_rows = _load_normalized_rows(run_id, "study1")
        prepared = _prepare_downstream_manifests(run_id, study1_rows, config)
        state["phase_counts"].update(prepared)
    elif phase == "STUDY2_WITHIN":
        jobs = _load_jobs_from_metadata(run_id, "study2_within")
        if not jobs:
            jobs = _submit_batch_jobs(run_id, "study2_within")
        if not _poll_batch_jobs(run_id, "study2_within", jobs, poll_interval_sec):
            return state
        _materialize_dryrun_batch_output_for_phase(run_id, "study2_within")
        rows, invalid_rows = _run_prediction_phase(run_id, "study2_within")
        state["phase_counts"]["study2_within"] = len(rows)
        state["invalid_counts"]["study2_within"] = len(invalid_rows)
    elif phase == "STUDY2_ACROSS":
        jobs = _load_jobs_from_metadata(run_id, "study2_across")
        if not jobs:
            jobs = _submit_batch_jobs(run_id, "study2_across")
        if not _poll_batch_jobs(run_id, "study2_across", jobs, poll_interval_sec):
            return state
        _materialize_dryrun_batch_output_for_phase(run_id, "study2_across")
        rows, invalid_rows = _run_prediction_phase(run_id, "study2_across")
        state["phase_counts"]["study2_across"] = len(rows)
        state["invalid_counts"]["study2_across"] = len(invalid_rows)
    elif phase == "EXPERIMENT_A":
        outcome = _run_experiment_a(run_id, models, shard_size, poll_interval_sec)
        if outcome is None:
            return state
        rows, invalid_rows = outcome
        state["phase_counts"]["experiment_a"] = len(rows)
        state["invalid_counts"]["experiment_a"] = len(invalid_rows)
    elif phase == "EXPERIMENT_D":
        outcome = _run_experiment_d(run_id, models, shard_size, poll_interval_sec)
        if outcome is None:
            return state
        rows, invalid_rows = outcome
        state["phase_counts"]["experiment_d"] = len(rows)
        state["invalid_counts"]["experiment_d"] = len(invalid_rows)
    elif phase == "REPORT":
        invalid_counts = {
            "study1": int(state.get("invalid_counts", {}).get("study1", 0)),
            "study2": int(state.get("invalid_counts", {}).get("study2_within", 0))
            + int(state.get("invalid_counts", {}).get("study2_across", 0)),
            "experiment_a": int(state.get("invalid_counts", {}).get("experiment_a", 0)),
            "experiment_d": int(state.get("invalid_counts", {}).get("experiment_d", 0)),
        }
        _write_reports(run_id, state.get("phase_counts", {}), invalid_counts)

    state["cursor"] = cursor + 1
    return state


def handler(event, _context):
    run_id = event.get("run_id")
    trace_id = str(event.get("trace_id") or uuid.uuid4())
    if not is_valid_run_id(run_id):
        return {
            "ok": False,
            "error": "run_id is invalid",
            "category": "validation",
            "trace_id": trace_id,
        }

    owner = str(uuid.uuid4())
    if not _acquire_lease(run_id, owner):
        _log("info", {"trace_id": trace_id, "run_id": run_id, "step": "LEASE", "message": "busy"})
        return {"ok": True, "run_id": run_id, "deferred": True}

    try:
        state = _load_state(run_id)
        for _ in range(MAX_PHASES_PER_INVOCATION):
            cursor = int(state.get("cursor", 0))
            if cursor >= len(PHASES):
                break

            phase = PHASES[cursor]
            _log(
                "info",
                {
                    "trace_id": trace_id,
                    "run_id": run_id,
                    "phase": phase,
                    "step": "PHASE_START",
                    "cursor": cursor,
                },
            )
            state = _execute_phase(run_id, state, trace_id)
            _save_state(run_id, state)
            _log(
                "info",
                {
                    "trace_id": trace_id,
                    "run_id": run_id,
                    "phase": phase,
                    "step": "PHASE_DONE",
                    "cursor": state.get("cursor"),
                },
            )

            if int(state.get("cursor", 0)) < len(PHASES):
                _invoke_self(run_id, trace_id)
                if MAX_PHASES_PER_INVOCATION == 1:
                    return {"ok": True, "run_id": run_id, "deferred": True}

        retry_count = int(state.get("retry_count", 0))
        if int(state.get("cursor", 0)) >= len(PHASES):
            invalid_total = sum(int(v) for v in state.get("invalid_counts", {}).values())
            if invalid_total > 0:
                _finalize(run_id, "PARTIAL", retry_count, trace_id)
                _emit_finalize_metrics(run_id, "PARTIAL", state)
                return {"ok": True, "run_id": run_id, "state": "PARTIAL"}
            _finalize(run_id, "SUCCEEDED", retry_count, trace_id)
            _emit_finalize_metrics(run_id, "SUCCEEDED", state)
            return {"ok": True, "run_id": run_id, "state": "SUCCEEDED"}
        return {"ok": True, "run_id": run_id, "deferred": True}
    except PipelineError as exc:
        state = _load_state(run_id)
        retry_count = int(state.get("retry_count", 0)) + 1
        state["retry_count"] = retry_count
        _save_state(run_id, state)
        _finalize(
            run_id,
            "FAILED",
            retry_count,
            trace_id,
            last_error={
                "step": exc.step,
                "reason": exc.reason,
                "retryable": exc.retryable,
                "category": exc.category,
            },
        )
        _emit_finalize_metrics(run_id, "FAILED", state)
        _log(
            "error",
            {
                "trace_id": trace_id,
                "run_id": run_id,
                "step": exc.step,
                "category": exc.category,
                "message": exc.reason,
            },
        )
        return {
            "ok": False,
            "run_id": run_id,
            "error": exc.reason,
            "category": exc.category,
            "retryable": exc.retryable,
            "trace_id": trace_id,
        }
    except Exception as exc:  # noqa: BLE001
        state = _load_state(run_id)
        retry_count = int(state.get("retry_count", 0)) + 1
        state["retry_count"] = retry_count
        _save_state(run_id, state)
        _finalize(
            run_id,
            "FAILED",
            retry_count,
            trace_id,
            last_error={
                "step": PHASES[min(int(state.get("cursor", 0)), len(PHASES) - 1)],
                "reason": str(exc),
                "retryable": False,
                "category": "internal",
            },
        )
        _emit_finalize_metrics(run_id, "FAILED", state)
        _log(
            "error",
            {
                "trace_id": trace_id,
                "run_id": run_id,
                "step": "UNHANDLED",
                "category": "internal",
                "message": str(exc),
            },
        )
        return {
            "ok": False,
            "run_id": run_id,
            "error": str(exc),
            "category": "internal",
            "trace_id": trace_id,
        }
    finally:
        _release_lease(run_id, owner)
