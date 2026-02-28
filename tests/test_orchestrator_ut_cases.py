import importlib
import os
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def mod():
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
    os.environ.setdefault("TABLE_NAME", "run_control_table")
    os.environ.setdefault("ARTIFACTS_BUCKET", "dummy-bucket")
    return importlib.import_module("app.orchestrator.handler")


def test_record_id_is_deterministic(mod):
    kwargs = {
        "run_id": "run-1",
        "phase": "study1",
        "model": "model-a",
        "target": "target-1",
        "prompt_type": "FACTUAL",
        "temperature": 0.5,
        "loop_index": 1,
    }

    first = mod._record_id(**kwargs)
    second = mod._record_id(**kwargs)

    assert first == second


def test_normalize_study1_writes_normalized_rows(mod):
    run_id = "run-1"
    output_key = f"runs/{run_id}/batch-output/study1/model-a/part-00001.jsonl"
    row = {
        "record_id": "r1",
        "model_id": "model-a",
        "temperature": 0.9,
        "prompt_type": "FACTUAL",
        "target": "x",
        "loop_index": 0,
        "generated_sentence": "hello",
        "reasoning": "ok",
        "judgment": "HIGH",
    }

    with (
        patch.object(mod, "_s3_list", return_value=[output_key]),
        patch.object(mod, "_s3_get_jsonl", return_value=[row]),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
    ):
        rows = mod._normalize_study1(run_id)

    assert len(rows) == 1
    assert rows[0]["judgment"] == "HIGH"
    out_key = f"runs/{run_id}/normalized/study1/model-a/part-00001.jsonl"
    put_jsonl.assert_called_once_with(out_key, rows)


def test_prediction_phase_writes_invalid_rows(mod):
    run_id = "run-2"
    output_key = f"runs/{run_id}/batch-output/study2_within/part-00001.jsonl"
    unparseable = {
        "source_record_id": "src-1",
        "generator_model": "g1",
        "predictor_model": "p1",
        "expected_label": "HIGH",
        "raw_text": "no high or low here",
    }

    with (
        patch.object(mod, "_s3_list", return_value=[output_key]),
        patch.object(mod, "_s3_get_jsonl", return_value=[unparseable]),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
    ):
        out_rows, invalid_rows = mod._run_prediction_phase(run_id, "study2_within")

    assert out_rows == []
    assert len(invalid_rows) == 1
    assert invalid_rows[0]["reason"] == "could not infer predicted_label from batch output"
    assert put_jsonl.call_count == 2


def test_submit_batch_jobs_retries_once_per_shard(mod):
    run_id = "run-3"
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
    run_id = "run-4"
    study1_rows = [{"model_id": "model-a"}]
    prediction_row = {
        "generator_model": "g1",
        "predictor_model": "p1",
        "expected_label": "HIGH",
        "predicted_label": "HIGH",
        "is_correct": True,
        "condition_type": "blind",
    }

    with (
        patch.object(mod.s3, "put_object") as put_object,
        patch.object(mod, "_s3_put_json") as put_json,
    ):
        mod._write_reports(
            run_id,
            study1_rows=study1_rows,
            within_rows=[prediction_row],
            across_rows=[prediction_row],
            experiment_a_rows=[prediction_row],
            experiment_d_rows=[prediction_row],
            phase_counts={"study1": 1},
        )

    keys = {kwargs["Key"] for _, kwargs in put_object.call_args_list}
    assert keys == {
        f"runs/{run_id}/reports/study1_summary.csv",
        f"runs/{run_id}/reports/study2_within.csv",
        f"runs/{run_id}/reports/study2_across.csv",
        f"runs/{run_id}/reports/experiment_a.csv",
        f"runs/{run_id}/reports/experiment_d.csv",
    }
    put_json.assert_called_once()
    assert put_json.call_args.args[0] == f"runs/{run_id}/reports/run_manifest.json"


def test_handler_tracks_step_transitions_and_succeeds(mod):
    with (
        patch.object(mod, "_load_config", return_value={"models": ["m1"], "shard_size": 100}),
        patch.object(mod, "_generate_study1_manifests", return_value=1),
        patch.object(mod, "_submit_batch_jobs", return_value={}),
        patch.object(mod, "_poll_batch_jobs"),
        patch.object(mod, "_materialize_dryrun_batch_output_for_phase"),
        patch.object(mod, "_normalize_study1", return_value=[{"model_id": "m1"}]),
        patch.object(mod, "_prepare_downstream_manifests", return_value={}),
        patch.object(mod, "_run_prediction_phase", side_effect=[([{}], []), ([{}], [])]),
        patch.object(mod, "_run_experiment_a", return_value=([{}], [])),
        patch.object(mod, "_run_experiment_d", return_value=([{}], [])),
        patch.object(mod, "_write_reports"),
        patch.object(mod, "_update_status") as update_status,
        patch.object(mod, "_finalize") as finalize,
    ):
        res = mod.handler({"run_id": "run-ok"}, None)

    assert res["ok"] is True
    finalize.assert_called_once_with("run-ok", "SUCCEEDED", 0)
    phases = [kwargs["phase"] for _, kwargs in update_status.call_args_list]
    assert phases == mod.PHASES


def test_handler_returns_partial_when_invalid_rows_exist(mod):
    with (
        patch.object(mod, "_load_config", return_value={"models": ["m1"], "shard_size": 100}),
        patch.object(mod, "_generate_study1_manifests", return_value=1),
        patch.object(mod, "_submit_batch_jobs", return_value={}),
        patch.object(mod, "_poll_batch_jobs"),
        patch.object(mod, "_materialize_dryrun_batch_output_for_phase"),
        patch.object(mod, "_normalize_study1", return_value=[{"model_id": "m1"}]),
        patch.object(mod, "_prepare_downstream_manifests", return_value={}),
        patch.object(
            mod, "_run_prediction_phase", side_effect=[([], [{"reason": "bad"}]), ([], [])]
        ),
        patch.object(mod, "_run_experiment_a", return_value=([], [])),
        patch.object(mod, "_run_experiment_d", return_value=([], [])),
        patch.object(mod, "_write_reports"),
        patch.object(mod, "_s3_get_json", return_value={"invalid_counts": {}}),
        patch.object(mod, "_s3_put_json"),
        patch.object(mod, "_update_status"),
        patch.object(mod, "_finalize") as finalize,
    ):
        res = mod.handler({"run_id": "run-partial"}, None)

    assert res["ok"] is True
    assert res["state"] == "PARTIAL"
    finalize.assert_called_once_with("run-partial", "PARTIAL", 0)


def test_handler_sets_error_category_and_retryable_on_pipeline_error(mod):
    err = mod.PipelineError(
        step="EXPERIMENT_A",
        reason="batch timeout",
        retryable=True,
        category="timeout",
    )
    with (
        patch.object(mod, "_load_config", side_effect=err),
        patch.object(mod, "_finalize") as finalize,
    ):
        res = mod.handler({"run_id": "run-fail"}, None)

    assert res["ok"] is False
    assert res["category"] == "timeout"
    assert res["retryable"] is True
    finalize.assert_called_once()
    args, kwargs = finalize.call_args
    assert args[0] == "run-fail"
    assert args[1] == "FAILED"
    assert args[2] == 1
    assert kwargs["last_error"]["step"] == "EXPERIMENT_A"
