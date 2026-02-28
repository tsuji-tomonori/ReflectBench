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
    assert invalid_rows[0]["reason"].startswith("schema validation failed")
    put_jsonl.assert_called_once()
    write_invalid.assert_called_once()


def test_submit_batch_jobs_retries_once_per_shard(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174002"
    manifest_key = f"runs/{run_id}/manifests/study1/model-a/part-00001.jsonl"

    with (
        patch.object(mod, "BATCH_DRY_RUN", False),
        patch.object(mod, "BEDROCK_BATCH_ROLE_ARN", "arn:aws:iam::123:role/bedrock-batch"),
        patch.object(mod, "_s3_list", return_value=[manifest_key]),
        patch.object(mod, "_model_id_from_manifest_key", return_value="model-a"),
        patch.object(mod.bedrock, "create_model_invocation_job") as submit_job,
        patch.object(mod, "_s3_put_json") as put_json,
    ):
        submit_job.side_effect = [Exception("temporary"), {"jobArn": "job-arn-1"}]
        jobs = mod._submit_batch_jobs(run_id, "study1")

    assert jobs[manifest_key] == "job-arn-1"
    assert submit_job.call_count == 2
    metadata_payload = put_json.call_args.args[1]
    assert metadata_payload["attempts"] == 2
    assert metadata_payload["status"] == "SUBMITTED"


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
