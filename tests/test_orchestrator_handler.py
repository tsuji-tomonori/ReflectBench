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


def test_record_id_is_deterministic(mod):
    first = mod._record_id(
        run_id="123e4567-e89b-42d3-a456-426614174000",
        phase="study1",
        model="m1",
        target="t",
        prompt_type="NORMAL",
        temperature=0.5,
        loop_index=0,
    )
    second = mod._record_id(
        run_id="123e4567-e89b-42d3-a456-426614174000",
        phase="study1",
        model="m1",
        target="t",
        prompt_type="NORMAL",
        temperature=0.5,
        loop_index=0,
    )
    assert first == second


def test_handler_rejects_invalid_run_id(mod):
    res = mod.handler({"run_id": "bad-id"}, None)
    assert res["ok"] is False
    assert res["category"] == "validation"


def test_handler_returns_deferred_when_lease_busy(mod):
    with patch.object(mod, "_acquire_lease", return_value=False):
        res = mod.handler({"run_id": "123e4567-e89b-42d3-a456-426614174000"}, None)
    assert res["ok"] is True
    assert res["deferred"] is True


def test_handler_finalizes_succeeded_when_all_phases_done(mod):
    done_state = {
        "cursor": len(mod.PHASES),
        "retry_count": 0,
        "invalid_counts": {},
        "phase_counts": {},
    }
    with (
        patch.object(mod, "_acquire_lease", return_value=True),
        patch.object(mod, "_load_state", return_value=done_state),
        patch.object(mod, "_finalize") as finalize,
        patch.object(mod, "_emit_finalize_metrics") as emit_metrics,
        patch.object(mod, "_release_lease"),
    ):
        res = mod.handler({"run_id": "123e4567-e89b-42d3-a456-426614174000"}, None)

    assert res["ok"] is True
    assert res["state"] == "SUCCEEDED"
    assert finalize.call_args.args[1] == "SUCCEEDED"
    assert emit_metrics.call_args.args[1] == "SUCCEEDED"


def test_handler_finalizes_partial_when_invalid_exists(mod):
    done_state = {
        "cursor": len(mod.PHASES),
        "retry_count": 0,
        "invalid_counts": {"study1": 1},
        "phase_counts": {},
    }
    with (
        patch.object(mod, "_acquire_lease", return_value=True),
        patch.object(mod, "_load_state", return_value=done_state),
        patch.object(mod, "_finalize") as finalize,
        patch.object(mod, "_emit_finalize_metrics") as emit_metrics,
        patch.object(mod, "_release_lease"),
    ):
        res = mod.handler({"run_id": "123e4567-e89b-42d3-a456-426614174000"}, None)

    assert res["ok"] is True
    assert res["state"] == "PARTIAL"
    assert finalize.call_args.args[1] == "PARTIAL"
    assert emit_metrics.call_args.args[1] == "PARTIAL"


def test_handler_returns_pipeline_error_model(mod):
    initial_state = {"cursor": 0, "retry_count": 0, "invalid_counts": {}, "phase_counts": {}}
    err = mod.PipelineError(
        step="STUDY1_BATCH_POLL",
        reason="poll timeout",
        retryable=True,
        category="timeout",
    )
    with (
        patch.object(mod, "_acquire_lease", return_value=True),
        patch.object(mod, "_load_state", side_effect=[dict(initial_state), dict(initial_state)]),
        patch.object(mod, "_execute_phase", side_effect=err),
        patch.object(mod, "_save_state"),
        patch.object(mod, "_finalize") as finalize,
        patch.object(mod, "_emit_finalize_metrics") as emit_metrics,
        patch.object(mod, "_release_lease"),
    ):
        res = mod.handler({"run_id": "123e4567-e89b-42d3-a456-426614174000"}, None)

    assert res["ok"] is False
    assert res["category"] == "timeout"
    assert res["retryable"] is True
    assert finalize.call_args.kwargs["last_error"]["step"] == "STUDY1_BATCH_POLL"
    assert emit_metrics.call_args.args[1] == "FAILED"


def test_emit_finalize_metrics_contains_required_names(mod):
    state = {"invalid_counts": {"study1": 2, "study2_within": 1}}
    with (
        patch.object(mod, "_run_duration_sec", return_value=42.0),
        patch.object(mod, "_sum_shard_retries", return_value=3),
        patch.object(mod, "_put_metric_data") as put_metric_data,
    ):
        mod._emit_finalize_metrics("123e4567-e89b-42d3-a456-426614174000", "SUCCEEDED", state)

    metric_names = {datum["MetricName"] for datum in put_metric_data.call_args.args[1]}
    assert "RunDurationSec" in metric_names
    assert "ParseFailureCount" in metric_names
    assert "ShardRetryCount" in metric_names
    assert "RunSucceeded" in metric_names
