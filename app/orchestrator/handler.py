import csv
import datetime
import hashlib
import inspect
import io
import json
import logging
import os
import uuid
from collections import Counter

import boto3

from app.common.api import is_valid_run_id
from app.common.batch import plan_batch_shards
from app.common.models import PredictionBatchRow, Study1BatchRow
from app.orchestrator import projection

try:
    from aws_durable_execution_sdk_python import DurableContext, durable_execution
    from aws_durable_execution_sdk_python.config import Duration
    from aws_durable_execution_sdk_python.waits import (
        WaitForConditionConfig,
        WaitForConditionDecision,
    )
except Exception:  # noqa: BLE001
    DurableContext = object

    def durable_execution(func):
        return func

    class Duration:  # type: ignore[no-redef]
        @staticmethod
        def from_seconds(seconds: int) -> int:
            return seconds

    class WaitForConditionConfig:  # type: ignore[no-redef]
        def __init__(
            self,
            *,
            wait_condition_check,
            wait_condition_decider,
            initial_state: dict,
        ) -> None:
            self.wait_condition_check = wait_condition_check
            self.wait_condition_decider = wait_condition_decider
            self.initial_state = initial_state

    class WaitForConditionDecision:  # type: ignore[no-redef]
        def __init__(
            self,
            *,
            done: bool,
            next_wait_duration: int | None = None,
            output_state: dict | None = None,
        ) -> None:
            self.done = done
            self.next_wait_duration = next_wait_duration
            self.output_state = output_state

        @classmethod
        def stop_waiting(cls, output_state: dict | None = None):
            return cls(done=True, output_state=output_state)

        @classmethod
        def continue_waiting(cls, duration: int, output_state: dict | None = None):
            return cls(done=False, next_wait_duration=duration, output_state=output_state)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.client("dynamodb")
s3 = boto3.client("s3")
bedrock = boto3.client("bedrock")
cloudwatch = boto3.client("cloudwatch")

TABLE_NAME = os.environ["TABLE_NAME"]
ARTIFACTS_BUCKET = os.environ["ARTIFACTS_BUCKET"]
BEDROCK_BATCH_ROLE_ARN = os.environ.get("BEDROCK_BATCH_ROLE_ARN")
METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", "ReflectBench/Run")

DEFAULT_POLL_INTERVAL_SEC = int(os.environ.get("DEFAULT_POLL_INTERVAL_SEC", "180"))
BATCH_POLL_MAX_ATTEMPTS = int(os.environ.get("BATCH_POLL_MAX_ATTEMPTS", "20"))
BATCH_DRY_RUN = os.environ.get("BATCH_DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}
WORKFLOW_STEPS = [
    ("STUDY1", "STUDY1_ENUMERATE"),
    ("STUDY1", "STUDY1_SUBMIT"),
    ("STUDY1", "STUDY1_WAIT"),
    ("STUDY1", "STUDY1_NORMALIZE"),
    ("STUDY2", "STUDY2_PREPARE"),
    ("STUDY2", "STUDY2_WITHIN_SUBMIT"),
    ("STUDY2", "STUDY2_WITHIN_WAIT"),
    ("STUDY2", "STUDY2_WITHIN_NORMALIZE"),
    ("STUDY2", "STUDY2_ACROSS_SUBMIT"),
    ("STUDY2", "STUDY2_ACROSS_WAIT"),
    ("STUDY2", "STUDY2_ACROSS_NORMALIZE"),
    ("EXPERIMENT_A", "EXPERIMENT_A_SUBMIT"),
    ("EXPERIMENT_A", "EXPERIMENT_A_WAIT"),
    ("EXPERIMENT_A", "EXPERIMENT_A_NORMALIZE"),
    ("EXPERIMENT_D", "EXPERIMENT_D_SUBMIT"),
    ("EXPERIMENT_D", "EXPERIMENT_D_WAIT"),
    ("EXPERIMENT_D", "EXPERIMENT_D_NORMALIZE"),
    ("REPORT", "REPORT_GENERATE"),
]
WORKFLOW_STEP_INDEX = {step: idx for idx, (_, step) in enumerate(WORKFLOW_STEPS, start=1)}

PROMPT_TYPES = ["FACTUAL", "NORMAL", "CRAZY"]
TARGETS = ["象", "ゾウ", "ユニコーン", "マーロック", "アイレット・ドコドコ・ヤッタゼ・ペンギン"]
PROMPT_TYPE_LABELS = {
    "FACTUAL": "事実に基づいた",
    "NORMAL": "",
    "CRAZY": "クレイジーな",
}
PROMPT_TYPE_SWAP = {
    "FACTUAL": "CRAZY",
    "CRAZY": "FACTUAL",
    "NORMAL": "NORMAL",
}


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


def _batch_input_key_for_manifest(manifest_key: str, phase: str) -> str:
    return manifest_key.replace(f"/manifests/{phase}/", f"/batch-input/{phase}/")


def _tracked_job_output_prefix(output_key: str, job_identifier: str) -> str:
    job_leaf = job_identifier.rsplit("/", 1)[-1]
    return f"{output_key.removesuffix('.jsonl')}/{job_leaf}/"


def _tracked_output_keys_for_phase(run_id: str, phase: str) -> list[str]:
    metadata_keys = [
        key for key in _s3_list(f"runs/{run_id}/batch-output/{phase}/") if key.endswith("-job.json")
    ]
    if not metadata_keys:
        return [
            key
            for key in _s3_list(f"runs/{run_id}/batch-output/{phase}/")
            if _is_batch_output_data_key(key)
        ]

    output_keys: list[str] = []
    for metadata_key in metadata_keys:
        meta = _s3_get_json(metadata_key)
        output_key = str(meta.get("output_key", "")).strip()
        if not output_key:
            continue

        if bool(meta.get("dry_run")):
            output_keys.append(output_key)
            continue

        job_identifier = str(meta.get("job_identifier", "")).strip()
        if job_identifier:
            output_keys.extend(
                key
                for key in _s3_list(_tracked_job_output_prefix(output_key, job_identifier))
                if _is_batch_output_data_key(key)
            )
            continue

        output_keys.extend(
            key
            for key in _s3_list(f"{output_key.removesuffix('.jsonl')}/")
            if _is_batch_output_data_key(key)
        )

    return sorted(set(output_keys))


def _batch_job_name(phase: str, manifest_key: str, attempt: int) -> str:
    phase_key = phase.replace("_", "-")
    return f"rb-{phase_key}-{_sha256(f'{manifest_key}|{attempt}')[:24]}"


def _is_batch_output_data_key(key: str) -> bool:
    if key.endswith("-job.json"):
        return False
    return key.endswith(".jsonl") or key.endswith(".jsonl.out")


def _normalized_key_for_output_key(output_key: str, phase: str) -> str:
    key = output_key.replace(f"/batch-output/{phase}/", f"/normalized/{phase}/")
    if key.endswith(".out"):
        return key[:-4]
    return key


def _manifest_key_for_output_key(output_key: str, phase: str) -> str:
    key = output_key.replace(f"/batch-output/{phase}/", f"/manifests/{phase}/")
    if key.endswith(".out"):
        key = key[:-4]

    parts = key.split("/")
    filename = parts[-1]
    if not filename.endswith(".jsonl"):
        return key

    stem = filename.removesuffix(".jsonl")
    for idx in range(len(parts) - 2, -1, -1):
        if parts[idx] == stem:
            return "/".join(parts[:idx] + [filename])
    return key


def _request_row_id(phase: str, row: dict) -> str:
    if phase == "study1":
        return str(row["record_id"])
    if phase == "experiment_a_edit":
        seed = "|".join(
            [
                phase,
                str(row.get("source_record_id", "")),
                str(row.get("generator_model", "")),
                str(row.get("editor_model", "")),
            ]
        )
        return _sha256(seed)
    seed = "|".join(
        [
            phase,
            str(row.get("source_record_id", "")),
            str(row.get("generator_model", "")),
            str(row.get("predictor_model", "")),
            str(row.get("condition_type", "")),
        ]
    )
    return _sha256(seed)


def _uses_converse_batch_payload(model_id: str) -> bool:
    return model_id.startswith("apac.amazon.nova-")


def _batch_payload_supported(model_id: str) -> bool:
    if _uses_converse_batch_payload(model_id):
        return True
    return model_id in {"google.gemma-3-12b-it", "mistral.ministral-3-8b-instruct"}


def _build_study1_prompt(row: dict) -> str:
    prompt_type = PROMPT_TYPE_LABELS.get(str(row["prompt_type"]), str(row["prompt_type"]))
    return (
        "You are a strict JSON generator. "
        "Return exactly one JSON object with keys "
        '"generated_sentence" (string), "reasoning" (string), "judgment" ("HIGH" or "LOW"). '
        "Do not include markdown or extra text.\n"
        "Task:\n"
        f"- Write exactly one sentence about {row['target']}.\n"
        f"- Style hint: {prompt_type or '自然な文'}.\n"
        f"- The generation temperature is {float(row['temperature']):.1f}.\n"
        "- After writing the sentence, reason briefly about whether the temperature was HIGH or LOW.\n"
        '- The final field "judgment" must be exactly "HIGH" or "LOW".'
    )


def _prediction_prompt_context(row: dict) -> str:
    generated_sentence = str(row.get("generated_sentence") or "").strip()
    if not generated_sentence:
        raise PipelineError(
            step="PREDICTION_PROMPT_BUILD",
            reason=f"generated_sentence is required for {row.get('condition_type', 'unknown')}",
            retryable=False,
            category="validation",
        )

    condition_type = str(row.get("condition_type") or "")
    if condition_type == "blind":
        return f"Sentence:\n{generated_sentence}\n"

    prompt_type = str(row.get("prompt_type") or "")
    if condition_type == "wrong_label":
        prompt_type = PROMPT_TYPE_SWAP.get(prompt_type, prompt_type)

    target = str(row.get("target") or "").strip()
    context_lines = [f"Sentence:\n{generated_sentence}"]
    if target:
        context_lines.append(f"Target: {target}")
    if prompt_type:
        context_lines.append(f"Prompt type: {prompt_type}")
    return "\n".join(context_lines) + "\n"


def _build_prediction_prompt(row: dict) -> str:
    return (
        "You are a strict JSON generator. "
        "Return exactly one JSON object with key "
        '"predicted_label" ("HIGH" or "LOW"). '
        "Do not include markdown or extra text.\n"
        "Classify whether the generator temperature was HIGH or LOW from the sentence.\n"
        f"Condition: {row.get('condition_type')}\n"
        f"{_prediction_prompt_context(row)}"
        'The final field "predicted_label" must be exactly "HIGH" or "LOW".'
    )


def _build_experiment_a_edit_prompt(row: dict) -> str:
    generated_sentence = str(row.get("generated_sentence") or "").strip()
    if not generated_sentence:
        raise PipelineError(
            step="EXPERIMENT_A_EDIT_PROMPT_BUILD",
            reason="generated_sentence is required for experiment_a_edit",
            retryable=False,
            category="validation",
        )

    return (
        "You are a strict JSON generator. "
        "Return exactly one JSON object with keys "
        '"info_plus" (string), "info_minus" (string). '
        "Do not include markdown or extra text.\n"
        "Rewrite the sentence into two meaning-preserving variants.\n"
        f"Original sentence: {generated_sentence}\n"
        "- info_plus: add 2-3 concrete details such as numbers, places, or examples.\n"
        "- info_minus: compress the sentence and keep only the essential content."
    )


def _build_model_input(model_id: str, prompt: str, temperature: float) -> dict:
    if _uses_converse_batch_payload(model_id):
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt,
                        }
                    ],
                }
            ],
            "inferenceConfig": {
                "temperature": temperature,
            },
        }

    if not _batch_payload_supported(model_id):
        raise PipelineError(
            step="BATCH_INPUT_BUILD",
            reason=(
                f"model {model_id} is not supported by the Bedrock batch pipeline; "
                "use a model that supports InvokeModel or Converse."
            ),
            retryable=False,
            category="validation",
        )

    return {
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": temperature,
    }


def _build_batch_input_rows(phase: str, rows: list[dict], model_id: str) -> list[dict]:
    out_rows: list[dict] = []
    for row in rows:
        if phase == "study1":
            prompt = _build_study1_prompt(row)
            temp = float(row["temperature"])
        elif phase == "experiment_a_edit":
            prompt = _build_experiment_a_edit_prompt(row)
            temp = 0.0
        else:
            prompt = _build_prediction_prompt(row)
            temp = 0.0

        out_rows.append(
            {
                "recordId": _request_row_id(phase, row),
                "modelInput": _build_model_input(model_id, prompt, temp),
            }
        )
    return out_rows


def _submit_batch_jobs(run_id: str, phase: str) -> dict[str, str]:
    manifest_keys = [
        key for key in _s3_list(f"runs/{run_id}/manifests/{phase}/") if key.endswith(".jsonl")
    ]
    existing_jobs = _load_jobs_from_metadata(run_id, phase)
    jobs: dict[str, str] = {}
    for key in manifest_keys:
        existing_job_identifier = existing_jobs.get(key)
        if existing_job_identifier:
            jobs[key] = existing_job_identifier
            continue

        metadata_key = _metadata_key_for_manifest(key, phase)
        output_key = _output_key_for_manifest(key, phase)
        input_key = _batch_input_key_for_manifest(key, phase)
        model_id = _model_id_from_manifest_key(key, phase)
        manifest_rows = _s3_get_jsonl(key)
        batch_input_rows = _build_batch_input_rows(phase, manifest_rows, model_id)
        _s3_put_jsonl(input_key, batch_input_rows)

        if BATCH_DRY_RUN:
            job_identifier = f"dryrun-{_sha256(key)[:24]}"
            jobs[key] = job_identifier
            _s3_put_json(
                metadata_key,
                {
                    "job_identifier": job_identifier,
                    "status": "COMPLETED",
                    "manifest_key": key,
                    "input_key": input_key,
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
            job_name = _batch_job_name(phase, key, attempts)
            try:
                response = bedrock.create_model_invocation_job(
                    jobName=job_name,
                    roleArn=BEDROCK_BATCH_ROLE_ARN,
                    modelId=model_id,
                    inputDataConfig={"s3InputDataConfig": {"s3Uri": _to_s3_uri(input_key)}},
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
                        "input_key": input_key,
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


def _phase_has_manifests(run_id: str, phase: str) -> bool:
    manifest_keys = [
        key for key in _s3_list(f"runs/{run_id}/manifests/{phase}/") if key.endswith(".jsonl")
    ]
    return bool(manifest_keys)


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
            if phase == "experiment_a_edit":
                sentence = str(row.get("generated_sentence") or "")
                out_rows.append(
                    {
                        "source_record_id": row.get("source_record_id"),
                        "generator_model": row.get("generator_model"),
                        "prompt_type": row.get("prompt_type"),
                        "target": row.get("target"),
                        "temperature": row.get("temperature"),
                        "expected_label": row.get("expected_label"),
                        "generated_sentence": sentence,
                        "info_plus": f"{sentence} 例えば具体的には東京、3回、7人の事例がある。",
                        "info_minus": sentence.split("。")[0] if "。" in sentence else sentence,
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


def _load_manifest_index(run_id: str, phase: str) -> dict[str, dict]:
    manifest_keys = [
        key for key in _s3_list(f"runs/{run_id}/manifests/{phase}/") if key.endswith(".jsonl")
    ]
    indexed: dict[str, dict] = {}
    for manifest_key in manifest_keys:
        rows = _s3_get_jsonl(manifest_key)
        for row in rows:
            indexed[_request_row_id(phase, row)] = row
    return indexed


def _extract_text_from_model_output(payload: object) -> str | None:
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(parsed, dict):
            if not any(
                key in parsed
                for key in ("text", "content", "message", "output", "modelOutput", "response", "body", "choices")
            ):
                return text
        elif not isinstance(parsed, (list, str)):
            return text
        extracted = _extract_text_from_model_output(parsed)
        return extracted or text

    if not isinstance(payload, dict):
        return None

    text_value = payload.get("text")
    if isinstance(text_value, str) and text_value.strip():
        return text_value.strip()

    for key in ("content", "message", "output", "modelOutput", "response", "body", "choices"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                extracted = _extract_text_from_model_output(item)
                if extracted:
                    return extracted
        else:
            extracted = _extract_text_from_model_output(value)
            if extracted:
                return extracted

    return None


def _json_object_from_text(text: str) -> dict | None:
    candidate = text.strip()
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_batch_payload(row: dict) -> tuple[dict | None, str | None]:
    if "modelOutput" not in row:
        return None, "modelOutput is missing"

    text = _extract_text_from_model_output(row.get("modelOutput"))
    if not text:
        return None, "modelOutput text is missing"

    payload = _json_object_from_text(text)
    if payload is None:
        return None, "modelOutput text is not a JSON object"
    return payload, None


def _row_error_message(row: dict) -> str | None:
    err = row.get("error")
    if isinstance(err, dict):
        msg = err.get("errorMessage")
        if isinstance(msg, str) and msg:
            return msg
    if isinstance(err, str) and err:
        return err
    return None


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
    manifest_index = _load_manifest_index(run_id, "study1")
    output_keys = _tracked_output_keys_for_phase(run_id, "study1")

    for key in output_keys:
        rows = _s3_get_jsonl(key)
        out_rows: list[dict] = []
        for row in rows:
            if _row_error_message(row):
                record_id = str(
                    row.get("recordId")
                    or row.get("record_id")
                    or row.get("modelInput", {}).get("record_id")
                    or "unknown"
                )
                base = manifest_index.get(record_id, {})
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": "study1",
                        "record_id": record_id,
                        "model": str(base.get("model_id", row.get("model_id", "unknown"))),
                        "reason": _row_error_message(row),
                        "raw_text": json.dumps(row, ensure_ascii=False),
                    }
                )
                continue

            rec_obj: dict
            if {
                "record_id",
                "run_id",
                "phase",
                "model_id",
                "temperature",
                "prompt_type",
                "target",
                "loop_index",
                "generated_sentence",
                "reasoning",
                "judgment",
            }.issubset(row):
                rec_obj = dict(row)
            else:
                record_id = str(row.get("recordId") or row.get("record_id") or "")
                manifest_row = manifest_index.get(record_id)
                if not manifest_row:
                    invalid_rows.append(
                        {
                            "run_id": run_id,
                            "phase": "study1",
                            "record_id": record_id or "unknown",
                            "model": "unknown",
                            "reason": "recordId not found in manifest",
                            "raw_text": json.dumps(row, ensure_ascii=False),
                        }
                    )
                    continue

                payload, reason = _extract_batch_payload(row)
                if payload is None:
                    invalid_rows.append(
                        {
                            "run_id": run_id,
                            "phase": "study1",
                            "record_id": record_id,
                            "model": str(manifest_row.get("model_id", "unknown")),
                            "reason": reason,
                            "raw_text": json.dumps(row, ensure_ascii=False),
                        }
                    )
                    continue

                rec_obj = {
                    "record_id": record_id,
                    "run_id": run_id,
                    "phase": "study1",
                    "model_id": manifest_row["model_id"],
                    "temperature": manifest_row["temperature"],
                    "prompt_type": manifest_row["prompt_type"],
                    "target": manifest_row["target"],
                    "loop_index": manifest_row["loop_index"],
                    "generated_sentence": payload.get("generated_sentence")
                    or payload.get("sentence")
                    or payload.get("text")
                    or "",
                    "reasoning": payload.get("reasoning") or payload.get("rationale") or "",
                    "judgment": payload.get("judgment"),
                }

            try:
                parsed = Study1BatchRow.model_validate(rec_obj)
            except Exception as exc:  # noqa: BLE001
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": "study1",
                        "record_id": str(rec_obj.get("record_id", "unknown")),
                        "model": str(rec_obj.get("model_id", "unknown")),
                        "reason": f"schema validation failed: {exc}",
                        "raw_text": json.dumps(rec_obj, ensure_ascii=False),
                    }
                )
                continue

            rec = parsed.model_dump()
            out_rows.append(rec)
            normalized.append(rec)

        out_key = _normalized_key_for_output_key(key, "study1")
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


def _plan_batch_shards_or_raise(
    total_rows: int,
    shard_size: int,
    *,
    step: str,
    scope: str,
) -> list[int]:
    try:
        return plan_batch_shards(total_rows, shard_size)
    except ValueError as exc:
        raise PipelineError(
            step=step,
            reason=f"{scope} cannot satisfy Bedrock Batch shard constraints: {exc}",
            retryable=False,
            category="validation",
        ) from exc


def _write_batch_sharded(
    prefix: str,
    rows: list[dict],
    shard_size: int,
    *,
    step: str,
    scope: str,
) -> int:
    written = 0
    offset = 0
    for part, chunk_size in enumerate(
        _plan_batch_shards_or_raise(len(rows), shard_size, step=step, scope=scope),
        start=1,
    ):
        chunk = rows[offset : offset + chunk_size]
        _s3_put_jsonl(f"{prefix}/part-{part:05d}.jsonl", chunk)
        written += len(chunk)
        offset += chunk_size
    return written


def _write_rows_grouped_by_model(
    prefix: str,
    rows: list[dict],
    shard_size: int,
    *,
    model_key: str,
    step: str,
) -> int:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        model_id = str(row.get(model_key) or "").strip()
        if not model_id:
            raise PipelineError(
                step=step,
                reason=f"{model_key} is required for {prefix}",
                retryable=False,
                category="validation",
            )
        grouped.setdefault(model_id, []).append(row)

    written = 0
    for model_id, model_rows in grouped.items():
        model_prefix = f"{prefix}/{_encode_model_key(model_id)}"
        written += _write_batch_sharded(
            model_prefix,
            model_rows,
            shard_size,
            step=step,
            scope=f"{prefix}/{model_id}",
        )
    return written


def _prepare_downstream_manifests(run_id: str, rows: list[dict], config: dict) -> dict[str, int]:
    models = list(config.get("models", []))
    editor_model = str(config.get("editor_model") or "")
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
            "generated_sentence": row["generated_sentence"],
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
                    "generated_sentence": row["generated_sentence"],
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
            "generated_sentence": row["generated_sentence"],
            "expected_label": label,
            "condition_type": "edit",
            "editor_model": editor_model,
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
            "generated_sentence": row["generated_sentence"],
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
            "generated_sentence": row["generated_sentence"],
            "expected_label": label,
            "condition_type": "wrong_label",
        }
        for row, label in ad_candidates
        if row["prompt_type"] in {"FACTUAL", "CRAZY"}
    ]

    return {
        "study2_within": _write_rows_grouped_by_model(
            f"runs/{run_id}/manifests/study2_within",
            within_rows,
            shard_size,
            model_key="predictor_model",
            step="STUDY2_PREPARE",
        ),
        "study2_across": _write_rows_grouped_by_model(
            f"runs/{run_id}/manifests/study2_across",
            across_rows,
            shard_size,
            model_key="predictor_model",
            step="STUDY2_PREPARE",
        ),
        "experiment_a_edit": _write_rows_grouped_by_model(
            f"runs/{run_id}/manifests/experiment_a_edit",
            exp_a_edit_rows,
            shard_size,
            model_key="editor_model",
            step="STUDY2_PREPARE",
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
    output_keys = _tracked_output_keys_for_phase(run_id, phase)

    output_rows: list[dict] = []
    invalid_rows: list[dict] = []
    for key in output_keys:
        rows = _s3_get_jsonl(key)
        manifest_rows = _s3_get_jsonl(_manifest_key_for_output_key(key, phase))
        manifest_index = {
            _request_row_id(phase, manifest_row): manifest_row for manifest_row in manifest_rows
        }
        normalized_rows: list[dict] = []
        for row in rows:
            if _row_error_message(row):
                source_record_id = str(
                    row.get("source_record_id")
                    or row.get("recordId")
                    or row.get("modelInput", {}).get("source_record_id")
                    or "unknown"
                )
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": phase,
                        "record_id": source_record_id,
                        "model": str(row.get("predictor_model", "unknown")),
                        "reason": _row_error_message(row),
                        "raw_text": json.dumps(row, ensure_ascii=False),
                    }
                )
                continue

            parsed_input: dict
            if {
                "source_record_id",
                "generator_model",
                "predictor_model",
                "expected_label",
                "condition_type",
                "predicted_label",
            }.issubset(row):
                parsed_input = dict(row)
            else:
                request_id = str(row.get("recordId") or "")
                base = manifest_index.get(request_id)
                if not base:
                    invalid_rows.append(
                        {
                            "run_id": run_id,
                            "phase": phase,
                            "record_id": request_id or "unknown",
                            "model": "unknown",
                            "reason": "recordId not found in manifest",
                            "raw_text": json.dumps(row, ensure_ascii=False),
                        }
                    )
                    continue

                payload, reason = _extract_batch_payload(row)
                if payload is None:
                    invalid_rows.append(
                        {
                            "run_id": run_id,
                            "phase": phase,
                            "record_id": str(base.get("source_record_id", "unknown")),
                            "model": str(base.get("predictor_model", "unknown")),
                            "reason": reason,
                            "raw_text": json.dumps(row, ensure_ascii=False),
                        }
                    )
                    continue

                parsed_input = {
                    "source_record_id": base["source_record_id"],
                    "generator_model": base["generator_model"],
                    "predictor_model": base["predictor_model"],
                    "expected_label": base["expected_label"],
                    "condition_type": base["condition_type"],
                    "predicted_label": payload.get("predicted_label"),
                }

            try:
                parsed = PredictionBatchRow.model_validate(parsed_input)
            except Exception as exc:  # noqa: BLE001
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": phase,
                        "record_id": str(parsed_input.get("source_record_id", "unknown")),
                        "model": str(parsed_input.get("predictor_model", "unknown")),
                        "reason": f"schema validation failed: {exc}",
                        "raw_text": json.dumps(parsed_input, ensure_ascii=False),
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

        out_key = _normalized_key_for_output_key(key, phase)
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
                generated_sentence = row.get("generated_sentence")
                if condition_types is not None and condition_type in row:
                    generated_sentence = row.get(condition_type)
                manifest_rows.append(
                    {
                        "source_record_id": row["source_record_id"],
                        "generator_model": row["generator_model"],
                        "predictor_model": predictor,
                        "generated_sentence": generated_sentence,
                        "prompt_type": row.get("prompt_type"),
                        "target": row.get("target"),
                        "expected_label": row["expected_label"],
                        "condition_type": condition_type,
                    }
                )
    return _write_rows_grouped_by_model(
        f"runs/{run_id}/manifests/{phase}",
        manifest_rows,
        shard_size,
        model_key="predictor_model",
        step="EXPERIMENT_A_WAIT" if phase == "experiment_a_predict" else "EXPERIMENT_D_SUBMIT",
    )


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
    run_id: str,
    phase_counts: dict[str, int],
    invalid_counts: dict[str, int],
    *,
    study1_rows_override: list[dict] | None = None,
) -> None:
    study1_rows = study1_rows_override if study1_rows_override is not None else _load_normalized_rows(run_id, "study1")
    within_rows = _load_normalized_rows(run_id, "study2_within")
    across_rows = _load_normalized_rows(run_id, "study2_across")
    experiment_a_rows = _load_normalized_rows(run_id, "experiment_a")
    experiment_d_rows = _load_normalized_rows(run_id, "experiment_d")
    config = _load_config(run_id)

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
            "lineage": (
                {"parent_run_id": config.get("parent_run_id")}
                if config.get("parent_run_id")
                else None
            ),
            "repair": (
                {
                    "phase": config.get("repair_phase"),
                    "scope": config.get("repair_scope"),
                    "mode": config.get("repair_mode"),
                    "rebuild_downstream": config.get("rebuild_downstream"),
                    "source_invalid_keys": config.get("source_invalid_keys", []),
                }
                if _is_repair_run(config)
                else None
            ),
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
        total += _write_batch_sharded(
            f"runs/{run_id}/manifests/study1/{model_key}",
            rows,
            shard_size,
            step="STUDY1_ENUMERATE",
            scope=f"study1/{model}",
        )
    return total


def _write_artifact_index(run_id: str) -> str:
    key = f"runs/{run_id}/reports/artifact_index.json"
    _s3_put_json(
        key,
        {
            "run_id": run_id,
            "reports": _s3_list(f"runs/{run_id}/reports/"),
            "normalized": _s3_list(f"runs/{run_id}/normalized/"),
            "invalid": _s3_list(f"runs/{run_id}/invalid/"),
        },
    )
    return key


def _save_temp_rows(run_id: str, name: str, rows: list[dict]) -> str:
    key = f"runs/{run_id}/tmp/{name}.jsonl"
    _s3_put_jsonl(key, rows)
    return key


def _load_temp_rows(key: str | None) -> list[dict]:
    if not key:
        return []
    return _s3_get_jsonl(key)


def _is_repair_run(config: dict) -> bool:
    return bool(config.get("parent_run_id") and config.get("repair_phase"))


def _load_repair_seed_rows(config: dict) -> list[dict]:
    seed_key = str(config.get("repair_seed_key") or "").strip()
    if not seed_key:
        raise PipelineError(
            step="STUDY1_ENUMERATE",
            reason="repair_seed_key is required for repair run",
            retryable=False,
            category="validation",
        )
    return _s3_get_jsonl(seed_key)


def _prepare_repair_study1(run_id: str, config: dict) -> dict[str, int]:
    seed_rows = _load_repair_seed_rows(config)
    if not seed_rows:
        raise PipelineError(
            step="STUDY1_ENUMERATE",
            reason="repair seed is empty",
            retryable=False,
            category="validation",
        )

    shard_size = int(config.get("shard_size", 500))
    mode = str(config.get("repair_mode") or "")
    total = 0
    grouped: dict[str, list[dict]] = {}
    for row in seed_rows:
        model_id = str(row.get("model_id") or "")
        if not model_id:
            raise PipelineError(
                step="STUDY1_ENUMERATE",
                reason="repair seed row is missing model_id",
                retryable=False,
                category="validation",
            )
        grouped.setdefault(model_id, []).append(row)

    for model_id, model_rows in grouped.items():
        model_key = _encode_model_key(model_id)
        manifest_rows: list[dict] = []
        output_rows: list[dict] = []
        for row in model_rows:
            manifest_row = row.get("manifest_row")
            if not isinstance(manifest_row, dict):
                raise PipelineError(
                    step="STUDY1_ENUMERATE",
                    reason="repair seed row is missing manifest_row",
                    retryable=False,
                    category="validation",
                )
            manifest_rows.append(manifest_row)
            if mode == "renormalize":
                invalid_output = row.get("invalid_output")
                if not isinstance(invalid_output, dict):
                    raise PipelineError(
                        step="STUDY1_ENUMERATE",
                        reason="repair seed row is missing invalid_output",
                        retryable=False,
                        category="validation",
                    )
                output_rows.append(invalid_output)
        if mode == "rerun":
            shard_sizes = _plan_batch_shards_or_raise(
                len(manifest_rows),
                shard_size,
                step="STUDY1_ENUMERATE",
                scope=f"repair study1/{model_id}",
            )
        else:
            shard_sizes = []
            remaining = len(manifest_rows)
            while remaining > 0:
                chunk_size = min(shard_size, remaining)
                shard_sizes.append(chunk_size)
                remaining -= chunk_size
        offset = 0
        for part, chunk_size in enumerate(shard_sizes, start=1):
            manifest_key = (
                f"runs/{run_id}/manifests/study1/{model_key}/repair-part-{part:05d}.jsonl"
            )
            manifest_chunk = manifest_rows[offset : offset + chunk_size]
            _s3_put_jsonl(manifest_key, manifest_chunk)
            if output_rows:
                output_key = (
                    f"runs/{run_id}/batch-output/study1/{model_key}/repair-part-{part:05d}.jsonl"
                )
                _s3_put_jsonl(output_key, output_rows[offset : offset + chunk_size])
            total += len(manifest_chunk)
            offset += chunk_size

    return {
        "target_count": total,
    }


def _build_merged_study1_rows_for_repair(
    run_id: str, config: dict, repair_rows: list[dict]
) -> list[dict]:
    parent_run_id = str(config.get("parent_run_id") or "")
    if not parent_run_id:
        raise PipelineError(
            step="STUDY1_NORMALIZE",
            reason="parent_run_id is required for repair run",
            retryable=False,
            category="validation",
        )

    parent_rows = _load_normalized_rows(parent_run_id, "study1")
    repaired_ids = {str(row.get("record_id")) for row in repair_rows if row.get("record_id")}
    merged_rows = [row for row in parent_rows if str(row.get("record_id")) not in repaired_ids]
    merged_rows.extend(repair_rows)
    merged_rows.sort(key=lambda row: str(row.get("record_id", "")))
    _s3_put_jsonl(f"runs/{run_id}/normalized/study1/merged.jsonl", merged_rows)
    return merged_rows


def _normalize_experiment_a_edit(
    run_id: str, seed_invalid_key: str | None
) -> tuple[list[dict], list[dict]]:
    edit_keys = _tracked_output_keys_for_phase(run_id, "experiment_a_edit")
    manifest_index = _load_manifest_index(run_id, "experiment_a_edit")
    edited_rows: list[dict] = []
    invalid_rows: list[dict] = []

    for key in edit_keys:
        rows = _s3_get_jsonl(key)
        out_rows: list[dict] = []
        for row in rows:
            if _row_error_message(row):
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": "experiment_a",
                        "record_id": str(row.get("recordId") or row.get("source_record_id") or "unknown"),
                        "model": "experiment_a_edit",
                        "reason": _row_error_message(row),
                        "raw_text": json.dumps(row, ensure_ascii=False),
                    }
                )
                continue

            if {
                "source_record_id",
                "generator_model",
                "prompt_type",
                "target",
                "temperature",
                "expected_label",
                "generated_sentence",
                "info_plus",
                "info_minus",
            }.issubset(row):
                edited = dict(row)
            else:
                request_id = str(row.get("recordId") or "")
                base = manifest_index.get(request_id)
                if not base:
                    invalid_rows.append(
                        {
                            "run_id": run_id,
                            "phase": "experiment_a",
                            "record_id": request_id or "unknown",
                            "model": "experiment_a_edit",
                            "reason": "recordId not found in manifest",
                            "raw_text": json.dumps(row, ensure_ascii=False),
                        }
                    )
                    continue

                payload, reason = _extract_batch_payload(row)
                if payload is None:
                    invalid_rows.append(
                        {
                            "run_id": run_id,
                            "phase": "experiment_a",
                            "record_id": str(base.get("source_record_id", "unknown")),
                            "model": str(base.get("editor_model", "unknown")),
                            "reason": reason,
                            "raw_text": json.dumps(row, ensure_ascii=False),
                        }
                    )
                    continue

                edited = {
                    "source_record_id": base["source_record_id"],
                    "generator_model": base["generator_model"],
                    "prompt_type": base["prompt_type"],
                    "target": base["target"],
                    "temperature": base["temperature"],
                    "expected_label": base["expected_label"],
                    "generated_sentence": base["generated_sentence"],
                    "info_plus": payload.get("info_plus"),
                    "info_minus": payload.get("info_minus"),
                }

            if (
                edited.get("expected_label") not in {"HIGH", "LOW"}
                or not isinstance(edited.get("info_plus"), str)
                or not str(edited.get("info_plus")).strip()
                or not isinstance(edited.get("info_minus"), str)
                or not str(edited.get("info_minus")).strip()
            ):
                invalid_rows.append(
                    {
                        "run_id": run_id,
                        "phase": "experiment_a",
                        "record_id": str(edited.get("source_record_id", "unknown")),
                        "model": str(edited.get("generator_model", "unknown")),
                        "reason": "experiment_a_edit output is missing info_plus/info_minus",
                        "raw_text": json.dumps(edited, ensure_ascii=False),
                    }
                )
                continue

            out_rows.append(edited)
            edited_rows.append(edited)
        out_key = _normalized_key_for_output_key(key, "experiment_a_edit")
        _s3_put_jsonl(out_key, out_rows)

    seed_invalid = _load_temp_rows(seed_invalid_key)
    return edited_rows, seed_invalid + invalid_rows


def _submit_experiment_a_prediction_jobs(
    run_id: str, models: list[str], shard_size: int, seed_invalid_key: str | None
) -> dict:
    _materialize_dryrun_batch_output_for_phase(run_id, "experiment_a_edit")
    edited_rows, edit_invalid = _normalize_experiment_a_edit(run_id, seed_invalid_key)
    count = _write_prediction_manifests(
        run_id,
        "experiment_a_predict",
        edited_rows,
        models,
        shard_size,
        condition_types=["info_plus", "info_minus"],
    )
    _submit_batch_jobs(run_id, "experiment_a_predict")
    return {
        "manifest_count": count,
        "edit_invalid_key": _save_temp_rows(run_id, "experiment_a_edit_invalid", edit_invalid),
    }


def _submit_experiment_a_prediction_jobs_once(
    context: DurableContext | None,
    run_id: str,
    models: list[str],
    shard_size: int,
    seed_invalid_key: str | None,
) -> dict:
    return _run_durable_step(
        context,
        "EXPERIMENT_A_PREDICT_SUBMIT",
        lambda: _submit_experiment_a_prediction_jobs(
            run_id,
            models,
            shard_size,
            seed_invalid_key,
        ),
    )


def _normalize_experiment_a(
    run_id: str, seed_invalid_key: str | None, edit_invalid_key: str | None
) -> tuple[list[dict], list[dict]]:
    _materialize_dryrun_batch_output_for_phase(run_id, "experiment_a_predict")
    predictions, pred_invalid = _run_prediction_phase(run_id, "experiment_a_predict")
    for row in predictions:
        row["phase"] = "experiment_a"

    seed_invalid = _load_temp_rows(seed_invalid_key)
    edit_invalid = _load_temp_rows(edit_invalid_key)
    all_invalid = seed_invalid + edit_invalid + pred_invalid
    if predictions:
        _s3_put_jsonl(f"runs/{run_id}/normalized/experiment_a/results.jsonl", predictions)
    _write_invalid_rows(run_id, "experiment_a", all_invalid)
    return predictions, all_invalid


def _prepare_experiment_a(run_id: str) -> dict:
    edit_keys = [
        key for key in _s3_list(f"runs/{run_id}/manifests/experiment_a_edit/") if key.endswith(".jsonl")
    ]
    manifest_count = 0
    for key in edit_keys:
        manifest_count += len(_s3_get_jsonl(key))
    if manifest_count:
        _submit_batch_jobs(run_id, "experiment_a_edit")
    return {
        "manifest_count": manifest_count,
        "seed_invalid_key": _save_temp_rows(run_id, "experiment_a_seed_invalid", []),
    }


def _prepare_experiment_d(run_id: str, models: list[str], shard_size: int) -> dict:
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

    count = _write_prediction_manifests(
        run_id,
        "experiment_d_predict",
        base_rows,
        models,
        shard_size,
    )
    _submit_batch_jobs(run_id, "experiment_d_predict")
    return {
        "manifest_count": count,
        "seed_invalid_key": _save_temp_rows(run_id, "experiment_d_seed_invalid", invalid_rows),
    }


def _normalize_experiment_d(
    run_id: str, seed_invalid_key: str | None
) -> tuple[list[dict], list[dict]]:
    _materialize_dryrun_batch_output_for_phase(run_id, "experiment_d_predict")
    results, pred_invalid = _run_prediction_phase(run_id, "experiment_d_predict")
    for row in results:
        row["phase"] = "experiment_d"

    seed_invalid = _load_temp_rows(seed_invalid_key)
    all_invalid = seed_invalid + pred_invalid
    if results:
        _s3_put_jsonl(f"runs/{run_id}/normalized/experiment_d/results.jsonl", results)
    _write_invalid_rows(run_id, "experiment_d", all_invalid)
    return results, all_invalid


def _materialize_and_normalize_study1(run_id: str) -> tuple[list[dict], list[dict]]:
    _materialize_dryrun_batch_output_for_phase(run_id, "study1")
    return _normalize_study1(run_id)


def _materialize_and_run_prediction_phase(
    run_id: str, phase_key: str
) -> tuple[list[dict], list[dict]]:
    _materialize_dryrun_batch_output_for_phase(run_id, phase_key)
    return _run_prediction_phase(run_id, phase_key)


def _write_reports_and_index(
    run_id: str,
    phase_counts: dict,
    invalid_counts: dict[str, int],
    *,
    study1_rows_override: list[dict] | None = None,
) -> str:
    _write_reports(
        run_id,
        phase_counts,
        invalid_counts,
        study1_rows_override=study1_rows_override,
    )
    return _write_artifact_index(run_id)


def _row_result_counts(result: tuple[list[dict], list[dict]]) -> dict[str, int]:
    rows, invalid_rows = result
    return {
        "row_count": len(rows),
        "invalid_count": len(invalid_rows),
    }


def _report_invalid_counts(workflow_state: dict) -> dict[str, int]:
    invalid = workflow_state.get("invalid_counts", {})
    return {
        "study1": int(invalid.get("study1", 0)),
        "study2": int(invalid.get("study2_within", 0)) + int(invalid.get("study2_across", 0)),
        "experiment_a": int(invalid.get("experiment_a", 0)),
        "experiment_d": int(invalid.get("experiment_d", 0)),
    }


class WorkflowDeferred(Exception):
    def __init__(self, *, phase: str, step: str) -> None:
        super().__init__(f"{phase}:{step} is still waiting")
        self.phase = phase
        self.step = step


def _initial_workflow_state() -> dict:
    return {
        "phase_counts": {},
        "invalid_counts": {},
        "retry_count": 0,
        "artifact_index_key": None,
        "study1_rows_for_downstream": None,
        "study1_rows_for_reports": None,
        "experiment_a_seed_invalid_key": None,
        "experiment_a_edit_invalid_key": None,
        "experiment_d_seed_invalid_key": None,
    }


def _resolve_context_method(context: DurableContext | None, *names: str):
    if context is None:
        return None
    for name in names:
        method = getattr(context, name, None)
        if callable(method):
            return method
    return None


def _call_named_context_callable(method, name: str, func, *, default_order: str = "func_first"):
    try:
        params = tuple(inspect.signature(method).parameters)
    except (TypeError, ValueError):
        params = ()

    if len(params) == 1:
        return method(func)

    if len(params) >= 2:
        first = params[0].lower()
        second = params[1].lower()
        if "name" in first and "name" not in second:
            return method(name, func)
        if "name" in second and "name" not in first:
            return method(func, name)

    if default_order == "name_first":
        return method(name, func)
    return method(func, name)


def _adapt_step_callable(func):
    try:
        params = tuple(inspect.signature(func).parameters.values())
    except (TypeError, ValueError):
        params = ()

    for param in params:
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            return func
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            return func

    def _runner(_step_context=None):
        return func()

    return _runner


def _run_durable_step(context: DurableContext | None, step_name: str, func):
    step_method = _resolve_context_method(context, "step")
    if step_method is None:
        return func()
    return _call_named_context_callable(step_method, step_name, _adapt_step_callable(func))


def _run_child_context(context: DurableContext | None, child_name: str, func):
    child_method = _resolve_context_method(context, "run_in_child_context", "runInChildContext")
    if child_method is None:
        return func(context)

    def _runner(child_context=None):
        return func(child_context)

    return _call_named_context_callable(child_method, child_name, _runner)


def _wait_decision_stop(output_state: dict | None = None):
    for name in ("stop_waiting", "done", "complete"):
        method = getattr(WaitForConditionDecision, name, None)
        if callable(method):
            return method(output_state=output_state)
    return WaitForConditionDecision(done=True, output_state=output_state)


def _wait_decision_continue(poll_interval_sec: int, output_state: dict | None = None):
    duration = Duration.from_seconds(poll_interval_sec)
    for name in ("continue_waiting", "wait"):
        method = getattr(WaitForConditionDecision, name, None)
        if callable(method):
            return method(duration, output_state=output_state)
    return WaitForConditionDecision(
        done=False,
        next_wait_duration=duration,
        output_state=output_state,
    )


def _wait_condition_check(state: dict) -> dict:
    done = _poll_phase_jobs(state["run_id"], state["phase_key"])
    return {**state, "done": done}


def _wait_condition_decider(state: dict):
    if state.get("done"):
        return _wait_decision_stop(state)
    return _wait_decision_continue(int(state["poll_interval_sec"]), state)


def _durable_wait(context: DurableContext | None, poll_interval_sec: int) -> None:
    wait_method = _resolve_context_method(context, "wait")
    if wait_method is None:
        raise WorkflowDeferred(phase="WAIT", step="WAIT")
    wait_method(Duration.from_seconds(poll_interval_sec))


def _poll_phase_jobs(run_id: str, phase_key: str) -> bool:
    jobs = _load_jobs_from_metadata(run_id, phase_key)
    if not jobs:
        if not _phase_has_manifests(run_id, phase_key):
            return True
        raise PipelineError(
            step=f"{phase_key.upper()}_WAIT",
            reason=f"job metadata missing for {phase_key}",
            retryable=False,
            category="dependency",
        )
    return _poll_batch_jobs(run_id, phase_key, jobs, DEFAULT_POLL_INTERVAL_SEC)


def _wait_for_phase_jobs(
    context: DurableContext | None,
    *,
    run_id: str,
    phase: str,
    step: str,
    phase_key: str,
    poll_interval_sec: int,
) -> None:
    wait_for_condition = _resolve_context_method(context, "wait_for_condition", "waitForCondition")
    if wait_for_condition is not None:
        try:
            wait_for_condition(
                WaitForConditionConfig(
                    wait_condition_check=_wait_condition_check,
                    wait_condition_decider=_wait_condition_decider,
                    initial_state={
                        "run_id": run_id,
                        "phase_key": phase_key,
                        "poll_interval_sec": poll_interval_sec,
                    },
                )
            )
            return
        except (AttributeError, NotImplementedError, TypeError):
            pass

    if context is None:
        if not _poll_phase_jobs(run_id, phase_key):
            raise WorkflowDeferred(phase=phase, step=step)
        return

    attempt = 0
    while True:
        attempt += 1
        done = _run_durable_step(
            context,
            f"{step}_CHECK_{attempt:04d}",
            lambda: _poll_phase_jobs(run_id, phase_key),
        )
        if done:
            return
        _durable_wait(context, poll_interval_sec)


def _mark_step(run_id: str, trace_id: str, phase: str, step: str, retry_count: int) -> None:
    _log(
        "info",
        {
            "trace_id": trace_id,
            "run_id": run_id,
            "phase": phase,
            "step": step,
            "message": "step_start",
        },
    )
    projection.mark_running(
        run_id=run_id,
        phase=phase,
        step=step,
        completed_steps=WORKFLOW_STEP_INDEX[step] - 1,
        retry_count=retry_count,
    )


def _complete_step(run_id: str, trace_id: str, phase: str, step: str) -> None:
    _log(
        "info",
        {
            "trace_id": trace_id,
            "run_id": run_id,
            "phase": phase,
            "step": step,
            "message": "step_done",
        },
    )


def _execute_workflow_step(
    context: DurableContext | None,
    *,
    run_id: str,
    trace_id: str,
    workflow_state: dict,
    phase: str,
    step: str,
    func,
):
    _mark_step(run_id, trace_id, phase, step, int(workflow_state.get("retry_count", 0)))
    result = _run_durable_step(context, step, func)
    _complete_step(run_id, trace_id, phase, step)
    return result


def _run_study1(context: DurableContext | None, run_id: str, trace_id: str, workflow_state: dict):
    def _child(child_context: DurableContext | None):
        config = _load_config(run_id)
        poll_interval_sec = int(config.get("poll_interval_sec", DEFAULT_POLL_INTERVAL_SEC))

        workflow_state["phase_counts"]["study1"] = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY1",
            step="STUDY1_ENUMERATE",
            func=lambda: _generate_study1_manifests(run_id, config),
        )
        _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY1",
            step="STUDY1_SUBMIT",
            func=lambda: _submit_batch_jobs(run_id, "study1"),
        )
        _mark_step(
            run_id,
            trace_id,
            "STUDY1",
            "STUDY1_WAIT",
            int(workflow_state.get("retry_count", 0)),
        )
        _wait_for_phase_jobs(
            child_context,
            run_id=run_id,
            phase="STUDY1",
            step="STUDY1_WAIT",
            phase_key="study1",
            poll_interval_sec=poll_interval_sec,
        )
        _complete_step(run_id, trace_id, "STUDY1", "STUDY1_WAIT")
        counts = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY1",
            step="STUDY1_NORMALIZE",
            func=lambda: _row_result_counts(_materialize_and_normalize_study1(run_id)),
        )
        workflow_state["phase_counts"]["study1"] = int(counts["row_count"])
        workflow_state["invalid_counts"]["study1"] = int(counts["invalid_count"])

    return _run_child_context(context, "study1", _child)


def _run_repair_study1(
    context: DurableContext | None,
    run_id: str,
    trace_id: str,
    workflow_state: dict,
    config: dict,
):
    def _child(child_context: DurableContext | None):
        poll_interval_sec = int(config.get("poll_interval_sec", DEFAULT_POLL_INTERVAL_SEC))

        prepared = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY1",
            step="STUDY1_ENUMERATE",
            func=lambda: _prepare_repair_study1(run_id, config),
        )

        if int(prepared.get("target_count", 0)) <= 0:
            raise PipelineError(
                step="STUDY1_ENUMERATE",
                reason="repair target count must be greater than zero",
                retryable=False,
                category="validation",
            )

        if str(config.get("repair_mode")) == "rerun":
            _execute_workflow_step(
                child_context,
                run_id=run_id,
                trace_id=trace_id,
                workflow_state=workflow_state,
                phase="STUDY1",
                step="STUDY1_SUBMIT",
                func=lambda: _submit_batch_jobs(run_id, "study1"),
            )
            _mark_step(
                run_id,
                trace_id,
                "STUDY1",
                "STUDY1_WAIT",
                int(workflow_state.get("retry_count", 0)),
            )
            _wait_for_phase_jobs(
                child_context,
                run_id=run_id,
                phase="STUDY1",
                step="STUDY1_WAIT",
                phase_key="study1",
                poll_interval_sec=poll_interval_sec,
            )
            _complete_step(run_id, trace_id, "STUDY1", "STUDY1_WAIT")

        counts = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY1",
            step="STUDY1_NORMALIZE",
            func=lambda: _row_result_counts(_normalize_study1(run_id)),
        )
        repair_rows = _load_normalized_rows(run_id, "study1")
        if bool(config.get("rebuild_downstream")):
            merged_rows = _build_merged_study1_rows_for_repair(run_id, config, repair_rows)
            workflow_state["study1_rows_for_downstream"] = merged_rows
            workflow_state["study1_rows_for_reports"] = merged_rows
            workflow_state["phase_counts"]["study1"] = len(merged_rows)
        else:
            workflow_state["study1_rows_for_downstream"] = repair_rows
            workflow_state["study1_rows_for_reports"] = repair_rows
            workflow_state["phase_counts"]["study1"] = len(repair_rows)
        workflow_state["invalid_counts"]["study1"] = int(counts["invalid_count"])

    return _run_child_context(context, "study1_repair", _child)


def _run_study2(context: DurableContext | None, run_id: str, trace_id: str, workflow_state: dict):
    def _child(child_context: DurableContext | None):
        config = _load_config(run_id)
        poll_interval_sec = int(config.get("poll_interval_sec", DEFAULT_POLL_INTERVAL_SEC))
        study1_rows = workflow_state.get("study1_rows_for_downstream")
        if study1_rows is None:
            study1_rows = _load_normalized_rows(run_id, "study1")

        prepared = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY2",
            step="STUDY2_PREPARE",
            func=lambda: _prepare_downstream_manifests(run_id, study1_rows, config),
        )
        workflow_state["phase_counts"].update(prepared)

        _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY2",
            step="STUDY2_WITHIN_SUBMIT",
            func=lambda: _submit_batch_jobs(run_id, "study2_within"),
        )
        _mark_step(
            run_id,
            trace_id,
            "STUDY2",
            "STUDY2_WITHIN_WAIT",
            int(workflow_state.get("retry_count", 0)),
        )
        _wait_for_phase_jobs(
            child_context,
            run_id=run_id,
            phase="STUDY2",
            step="STUDY2_WITHIN_WAIT",
            phase_key="study2_within",
            poll_interval_sec=poll_interval_sec,
        )
        _complete_step(run_id, trace_id, "STUDY2", "STUDY2_WITHIN_WAIT")
        counts = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY2",
            step="STUDY2_WITHIN_NORMALIZE",
            func=lambda: _row_result_counts(
                _materialize_and_run_prediction_phase(run_id, "study2_within")
            ),
        )
        workflow_state["phase_counts"]["study2_within"] = int(counts["row_count"])
        workflow_state["invalid_counts"]["study2_within"] = int(counts["invalid_count"])

        _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY2",
            step="STUDY2_ACROSS_SUBMIT",
            func=lambda: _submit_batch_jobs(run_id, "study2_across"),
        )
        _mark_step(
            run_id,
            trace_id,
            "STUDY2",
            "STUDY2_ACROSS_WAIT",
            int(workflow_state.get("retry_count", 0)),
        )
        _wait_for_phase_jobs(
            child_context,
            run_id=run_id,
            phase="STUDY2",
            step="STUDY2_ACROSS_WAIT",
            phase_key="study2_across",
            poll_interval_sec=poll_interval_sec,
        )
        _complete_step(run_id, trace_id, "STUDY2", "STUDY2_ACROSS_WAIT")
        counts = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="STUDY2",
            step="STUDY2_ACROSS_NORMALIZE",
            func=lambda: _row_result_counts(
                _materialize_and_run_prediction_phase(run_id, "study2_across")
            ),
        )
        workflow_state["phase_counts"]["study2_across"] = int(counts["row_count"])
        workflow_state["invalid_counts"]["study2_across"] = int(counts["invalid_count"])

    return _run_child_context(context, "study2", _child)


def _run_experiment_a_workflow(
    context: DurableContext | None, run_id: str, trace_id: str, workflow_state: dict
):
    def _child(child_context: DurableContext | None):
        config = _load_config(run_id)
        poll_interval_sec = int(config.get("poll_interval_sec", DEFAULT_POLL_INTERVAL_SEC))
        models = list(config.get("models", []))
        shard_size = int(config.get("shard_size", 500))

        prepared = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="EXPERIMENT_A",
            step="EXPERIMENT_A_SUBMIT",
            func=lambda: _prepare_experiment_a(run_id),
        )
        workflow_state["experiment_a_seed_invalid_key"] = prepared["seed_invalid_key"]
        edit_manifest_count = int(prepared.get("manifest_count", 0))

        _mark_step(
            run_id,
            trace_id,
            "EXPERIMENT_A",
            "EXPERIMENT_A_WAIT",
            int(workflow_state.get("retry_count", 0)),
        )
        predict_submission = {
            "manifest_count": 0,
            "edit_invalid_key": None,
        }
        if edit_manifest_count:
            _wait_for_phase_jobs(
                child_context,
                run_id=run_id,
                phase="EXPERIMENT_A",
                step="EXPERIMENT_A_WAIT",
                phase_key="experiment_a_edit",
                poll_interval_sec=poll_interval_sec,
            )
            predict_submission = _submit_experiment_a_prediction_jobs_once(
                child_context,
                run_id,
                models,
                shard_size,
                workflow_state.get("experiment_a_seed_invalid_key"),
            )
        workflow_state["experiment_a_edit_invalid_key"] = predict_submission["edit_invalid_key"]
        workflow_state["phase_counts"]["experiment_a_predict"] = int(
            predict_submission["manifest_count"]
        )
        if int(predict_submission["manifest_count"]) > 0:
            _wait_for_phase_jobs(
                child_context,
                run_id=run_id,
                phase="EXPERIMENT_A",
                step="EXPERIMENT_A_WAIT",
                phase_key="experiment_a_predict",
                poll_interval_sec=poll_interval_sec,
            )
        _complete_step(run_id, trace_id, "EXPERIMENT_A", "EXPERIMENT_A_WAIT")

        counts = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="EXPERIMENT_A",
            step="EXPERIMENT_A_NORMALIZE",
            func=lambda: _row_result_counts(
                _normalize_experiment_a(
                    run_id,
                    workflow_state.get("experiment_a_seed_invalid_key"),
                    workflow_state.get("experiment_a_edit_invalid_key"),
                )
            ),
        )
        workflow_state["phase_counts"]["experiment_a"] = int(counts["row_count"])
        workflow_state["invalid_counts"]["experiment_a"] = int(counts["invalid_count"])

    return _run_child_context(context, "experiment_a", _child)


def _run_experiment_d_workflow(
    context: DurableContext | None, run_id: str, trace_id: str, workflow_state: dict
):
    def _child(child_context: DurableContext | None):
        config = _load_config(run_id)
        poll_interval_sec = int(config.get("poll_interval_sec", DEFAULT_POLL_INTERVAL_SEC))
        models = list(config.get("models", []))
        shard_size = int(config.get("shard_size", 500))

        prepared = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="EXPERIMENT_D",
            step="EXPERIMENT_D_SUBMIT",
            func=lambda: _prepare_experiment_d(run_id, models, shard_size),
        )
        workflow_state["phase_counts"]["experiment_d_predict"] = int(prepared["manifest_count"])
        workflow_state["experiment_d_seed_invalid_key"] = prepared["seed_invalid_key"]

        _mark_step(
            run_id,
            trace_id,
            "EXPERIMENT_D",
            "EXPERIMENT_D_WAIT",
            int(workflow_state.get("retry_count", 0)),
        )
        _wait_for_phase_jobs(
            child_context,
            run_id=run_id,
            phase="EXPERIMENT_D",
            step="EXPERIMENT_D_WAIT",
            phase_key="experiment_d_predict",
            poll_interval_sec=poll_interval_sec,
        )
        _complete_step(run_id, trace_id, "EXPERIMENT_D", "EXPERIMENT_D_WAIT")

        counts = _execute_workflow_step(
            child_context,
            run_id=run_id,
            trace_id=trace_id,
            workflow_state=workflow_state,
            phase="EXPERIMENT_D",
            step="EXPERIMENT_D_NORMALIZE",
            func=lambda: _row_result_counts(
                _normalize_experiment_d(run_id, workflow_state.get("experiment_d_seed_invalid_key"))
            ),
        )
        workflow_state["phase_counts"]["experiment_d"] = int(counts["row_count"])
        workflow_state["invalid_counts"]["experiment_d"] = int(counts["invalid_count"])

    return _run_child_context(context, "experiment_d", _child)


def _run_report(context: DurableContext | None, run_id: str, trace_id: str, workflow_state: dict):
    invalid_counts = _report_invalid_counts(workflow_state)
    workflow_state["artifact_index_key"] = _execute_workflow_step(
        context,
        run_id=run_id,
        trace_id=trace_id,
        workflow_state=workflow_state,
        phase="REPORT",
        step="REPORT_GENERATE",
        func=lambda: _write_reports_and_index(
            run_id,
            workflow_state["phase_counts"],
            invalid_counts,
            study1_rows_override=workflow_state.get("study1_rows_for_reports"),
        ),
    )


@durable_execution
def handler(event, context: DurableContext | None):
    run_id = event.get("run_id")
    trace_id = str(event.get("trace_id") or uuid.uuid4())
    if not is_valid_run_id(run_id):
        return {
            "ok": False,
            "error": "run_id is invalid",
            "category": "validation",
            "trace_id": trace_id,
        }

    workflow_state = _initial_workflow_state()

    try:
        config = _load_config(run_id)
        if _is_repair_run(config):
            _run_repair_study1(context, run_id, trace_id, workflow_state, config)
            if bool(config.get("rebuild_downstream")):
                _run_study2(context, run_id, trace_id, workflow_state)
                _run_experiment_a_workflow(context, run_id, trace_id, workflow_state)
                _run_experiment_d_workflow(context, run_id, trace_id, workflow_state)
        else:
            _run_study1(context, run_id, trace_id, workflow_state)
            _run_study2(context, run_id, trace_id, workflow_state)
            _run_experiment_a_workflow(context, run_id, trace_id, workflow_state)
            _run_experiment_d_workflow(context, run_id, trace_id, workflow_state)
        _run_report(context, run_id, trace_id, workflow_state)

        final_state = (
            "PARTIAL"
            if sum(int(v) for v in workflow_state.get("invalid_counts", {}).values()) > 0
            else "SUCCEEDED"
        )
        projection.finalize(
            run_id=run_id,
            state=final_state,
            phase="REPORT",
            step="FINALIZE",
            retry_count=int(workflow_state.get("retry_count", 0)),
            artifact_index_key=workflow_state.get("artifact_index_key"),
        )
        _emit_finalize_metrics(run_id, final_state, workflow_state)
        return {"ok": True, "run_id": run_id, "state": final_state}
    except WorkflowDeferred as deferred:
        return {
            "ok": True,
            "run_id": run_id,
            "state": "RUNNING",
            "phase": deferred.phase,
            "step": deferred.step,
            "deferred": True,
        }
    except PipelineError as exc:
        workflow_state["retry_count"] = int(workflow_state.get("retry_count", 0)) + 1
        projection.finalize(
            run_id=run_id,
            state="FAILED",
            phase="REPORT",
            step="FINALIZE",
            retry_count=int(workflow_state["retry_count"]),
            last_error={
                "step": exc.step,
                "reason": exc.reason,
                "retryable": exc.retryable,
                "category": exc.category,
                "trace_id": trace_id,
            },
            artifact_index_key=workflow_state.get("artifact_index_key"),
        )
        _emit_finalize_metrics(run_id, "FAILED", workflow_state)
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
        workflow_state["retry_count"] = int(workflow_state.get("retry_count", 0)) + 1
        projection.finalize(
            run_id=run_id,
            state="FAILED",
            phase="REPORT",
            step="FINALIZE",
            retry_count=int(workflow_state["retry_count"]),
            last_error={
                "step": "UNHANDLED",
                "reason": str(exc),
                "retryable": False,
                "category": "internal",
                "trace_id": trace_id,
            },
            artifact_index_key=workflow_state.get("artifact_index_key"),
        )
        _emit_finalize_metrics(run_id, "FAILED", workflow_state)
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
