import importlib
import os
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def mod():
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
    os.environ.setdefault("TABLE_NAME", "run_control_table")
    os.environ.setdefault("ARTIFACTS_BUCKET", "dummy-bucket")
    os.environ.setdefault("BATCH_DRY_RUN", "true")
    return importlib.import_module("app.orchestrator.handler")


def test_normalize_study1_writes_normalized_and_invalid(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174000"
    output_key = f"runs/{run_id}/batch-output/study1/model-a/part-00001.jsonl"
    valid = {
        "record_id": "r1",
        "run_id": run_id,
        "phase": "study1",
        "model_id": "model-a",
        "temperature": 0.9,
        "prompt_type": "FACTUAL",
        "target": "x",
        "loop_index": 0,
        "generated_sentence": "hello",
        "reasoning": "ok",
        "judgment": "HIGH",
    }
    invalid = {
        "record_id": "r2",
        "phase": "study1",
        "model_id": "model-a",
    }

    with (
        patch.object(mod, "_s3_list", return_value=[output_key]),
        patch.object(mod, "_s3_get_jsonl", return_value=[valid, invalid]),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
        patch.object(mod, "_write_invalid_rows") as write_invalid,
    ):
        rows, invalid_rows = mod._normalize_study1(run_id)

    assert len(rows) == 1
    assert len(invalid_rows) == 1
    put_jsonl.assert_called_once()
    write_invalid.assert_called_once()


def test_prediction_phase_writes_invalid_rows(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174001"
    output_key = f"runs/{run_id}/batch-output/study2_within/part-00001.jsonl"
    invalid = {
        "source_record_id": "src-1",
        "generator_model": "g1",
        "predictor_model": "p1",
        "expected_label": "HIGH",
    }

    with (
        patch.object(mod, "_s3_list", return_value=[output_key]),
        patch.object(mod, "_s3_get_jsonl", return_value=[invalid]),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
        patch.object(mod, "_write_invalid_rows") as write_invalid,
    ):
        out_rows, invalid_rows = mod._run_prediction_phase(run_id, "study2_within")

    assert out_rows == []
    assert len(invalid_rows) == 1
    assert invalid_rows[0]["reason"] == "recordId not found in manifest"
    put_jsonl.assert_called_once()
    write_invalid.assert_called_once()


def test_submit_batch_jobs_retries_once_per_shard(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174002"
    manifest_key = f"runs/{run_id}/manifests/study1/model-a/part-00001.jsonl"
    manifest_row = {
        "record_id": "r-1",
        "run_id": run_id,
        "phase": "study1",
        "model_id": "model-a",
        "temperature": 0.3,
        "prompt_type": "FACTUAL",
        "target": "x",
        "loop_index": 0,
    }

    with (
        patch.object(mod, "BATCH_DRY_RUN", False),
        patch.object(mod, "BEDROCK_BATCH_ROLE_ARN", "arn:aws:iam::123:role/bedrock-batch"),
        patch.object(mod, "_s3_list", return_value=[manifest_key]),
        patch.object(mod, "_s3_get_jsonl", return_value=[manifest_row]),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
        patch.object(mod, "_model_id_from_manifest_key", return_value="model-a"),
        patch.object(mod.bedrock, "create_model_invocation_job") as submit_job,
        patch.object(mod, "_s3_put_json") as put_json,
    ):
        submit_job.side_effect = [Exception("temporary"), {"jobArn": "job-arn-1"}]
        jobs = mod._submit_batch_jobs(run_id, "study1")

    assert jobs[manifest_key] == "job-arn-1"
    assert submit_job.call_count == 2
    put_jsonl.assert_called_once()
    metadata_payload = put_json.call_args.args[1]
    assert metadata_payload["attempts"] == 2
    assert metadata_payload["status"] == "SUBMITTED"


def test_build_batch_input_rows_contains_messages(mod):
    rows = [
        {
            "record_id": "r-1",
            "run_id": "123e4567-e89b-42d3-a456-426614174000",
            "phase": "study1",
            "model_id": "model-a",
            "temperature": 0.0,
            "prompt_type": "FACTUAL",
            "target": "x",
            "loop_index": 0,
        }
    ]

    out = mod._build_batch_input_rows("study1", rows)

    assert len(out) == 1
    assert out[0]["recordId"] == "r-1"
    assert out[0]["modelInput"]["messages"][0]["role"] == "user"
    assert out[0]["modelInput"]["messages"][0]["content"][0]["text"]


def test_normalize_study1_parses_batch_wrapper(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174099"
    manifest_key = f"runs/{run_id}/manifests/study1/model-a/part-00001.jsonl"
    output_key = f"runs/{run_id}/batch-output/study1/model-a/part-00001.jsonl"
    record_id = "rec-1"
    manifest_row = {
        "record_id": record_id,
        "run_id": run_id,
        "phase": "study1",
        "model_id": "model-a",
        "temperature": 0.9,
        "prompt_type": "FACTUAL",
        "target": "x",
        "loop_index": 0,
    }
    wrapped_output = {
        "recordId": record_id,
        "modelOutput": {
            "output": {
                "message": {
                    "content": [
                        {"text": '{"generated_sentence":"s","reasoning":"r","judgment":"HIGH"}'}
                    ]
                }
            }
        },
    }

    with (
        patch.object(mod, "_s3_list") as s3_list,
        patch.object(mod, "_s3_get_jsonl") as s3_get_jsonl,
        patch.object(mod, "_s3_put_jsonl") as s3_put_jsonl,
        patch.object(mod, "_write_invalid_rows") as write_invalid,
    ):
        s3_list.side_effect = [[manifest_key], [output_key]]
        s3_get_jsonl.side_effect = [[manifest_row], [wrapped_output]]

        rows, invalid_rows = mod._normalize_study1(run_id)

    assert len(rows) == 1
    assert rows[0]["record_id"] == record_id
    assert rows[0]["judgment"] == "HIGH"
    assert invalid_rows == []
    s3_put_jsonl.assert_called_once()
    write_invalid.assert_called_once_with(run_id, "study1", [])


def test_poll_batch_jobs_returns_false_when_job_still_running(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174010"
    jobs = {f"runs/{run_id}/manifests/study1/model-a/part-00001.jsonl": "job-1"}

    with (
        patch.object(mod, "BATCH_DRY_RUN", False),
        patch.object(
            mod.bedrock, "get_model_invocation_job", return_value={"status": "InProgress"}
        ),
    ):
        done = mod._poll_batch_jobs(run_id, "study1", jobs, 180)

    assert done is False


def test_execute_phase_keeps_cursor_when_study1_poll_pending(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174011"
    state = {
        "cursor": mod.PHASES.index("STUDY1_BATCH_POLL"),
        "retry_count": 0,
        "phase_counts": {},
        "invalid_counts": {},
    }

    with (
        patch.object(
            mod,
            "_load_config",
            return_value={"poll_interval_sec": 180, "shard_size": 500, "models": []},
        ),
        patch.object(mod, "_update_status"),
        patch.object(mod, "_load_jobs_from_metadata", return_value={"manifest": "job"}),
        patch.object(mod, "_poll_batch_jobs", return_value=False),
    ):
        next_state = mod._execute_phase(run_id, state, "trace-1")

    assert next_state["cursor"] == mod.PHASES.index("STUDY1_BATCH_POLL")


def test_run_experiment_a_returns_none_when_poll_pending(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174012"

    with (
        patch.object(mod, "_s3_list", return_value=[]),
        patch.object(mod, "_write_prediction_manifests"),
        patch.object(mod, "_load_jobs_from_metadata", return_value={"manifest": "job"}),
        patch.object(mod, "_poll_batch_jobs", return_value=False),
        patch.object(mod, "_run_prediction_phase") as run_prediction,
    ):
        out = mod._run_experiment_a(run_id, ["model-a"], 500, 180)

    assert out is None
    run_prediction.assert_not_called()


def test_write_reports_outputs_required_artifacts(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174003"
    with (
        patch.object(mod, "_load_normalized_rows") as load_rows,
        patch.object(mod.s3, "put_object") as put_object,
        patch.object(mod, "_s3_put_json") as put_json,
    ):
        load_rows.side_effect = [
            [{"model_id": "model-a"}],
            [
                {
                    "generator_model": "g1",
                    "predictor_model": "p1",
                    "expected_label": "HIGH",
                    "predicted_label": "HIGH",
                    "is_correct": True,
                }
            ],
            [
                {
                    "generator_model": "g1",
                    "predictor_model": "p1",
                    "expected_label": "HIGH",
                    "predicted_label": "HIGH",
                    "is_correct": True,
                }
            ],
            [
                {
                    "condition_type": "info_plus",
                    "generator_model": "g1",
                    "predictor_model": "p1",
                    "expected_label": "HIGH",
                    "predicted_label": "HIGH",
                    "is_correct": True,
                }
            ],
            [
                {
                    "condition_type": "blind",
                    "generator_model": "g1",
                    "predictor_model": "p1",
                    "expected_label": "HIGH",
                    "predicted_label": "HIGH",
                    "is_correct": True,
                }
            ],
        ]
        mod._write_reports(
            run_id, {"study1": 1}, {"study1": 0, "study2": 0, "experiment_a": 0, "experiment_d": 0}
        )

    keys = {kwargs["Key"] for _, kwargs in put_object.call_args_list}
    assert f"runs/{run_id}/reports/study1_summary.csv" in keys
    assert f"runs/{run_id}/reports/study2_within.csv" in keys
    assert f"runs/{run_id}/reports/study2_across.csv" in keys
    assert f"runs/{run_id}/reports/experiment_a.csv" in keys
    assert f"runs/{run_id}/reports/experiment_d.csv" in keys
    put_json.assert_called_once()
