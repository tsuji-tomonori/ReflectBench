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


class FakeDurableContext:
    def __init__(self):
        self.steps = []
        self.child_contexts = []
        self.wait_configs = []

    def step(self, func, name):
        self.steps.append(name)
        return func()

    def run_in_child_context(self, func, name):
        self.child_contexts.append(name)
        return func(self)

    def wait_for_condition(self, config):
        self.wait_configs.append(config)
        return {"done": True}



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


def test_handler_returns_deferred_when_pending_without_durable_context(mod):
    with (
        patch.object(mod, "_load_config", return_value={"poll_interval_sec": 10}),
        patch.object(mod, "_generate_study1_manifests", return_value=1),
        patch.object(mod, "_submit_batch_jobs", return_value={"manifest": "job-1"}),
        patch.object(mod, "_load_jobs_from_metadata", return_value={"manifest": "job-1"}),
        patch.object(mod, "_poll_batch_jobs", return_value=False),
        patch.object(mod.projection, "mark_running"),
    ):
        res = mod.handler({"run_id": "123e4567-e89b-42d3-a456-426614174000"}, None)

    assert res["ok"] is True
    assert res["deferred"] is True
    assert res["phase"] == "STUDY1"
    assert res["step"] == "STUDY1_WAIT"


def test_handler_uses_child_context_and_wait_for_condition(mod):
    context = FakeDurableContext()

    with (
        patch.object(
            mod,
            "_load_config",
            return_value={"poll_interval_sec": 10, "models": [], "shard_size": 500},
        ),
        patch.object(mod, "_generate_study1_manifests", return_value=1),
        patch.object(mod, "_submit_batch_jobs", return_value={"manifest": "job-1"}),
        patch.object(mod, "_normalize_study1", return_value=([], [])),
        patch.object(mod, "_prepare_downstream_manifests", return_value={}),
        patch.object(mod, "_load_normalized_rows", return_value=[]),
        patch.object(mod, "_run_prediction_phase", return_value=([], [])),
        patch.object(mod, "_materialize_dryrun_batch_output_for_phase"),
        patch.object(
            mod,
            "_prepare_experiment_a",
            return_value={"manifest_count": 0, "seed_invalid_key": None},
        ),
        patch.object(
            mod,
            "_prepare_experiment_d",
            return_value={"manifest_count": 0, "seed_invalid_key": None},
        ),
        patch.object(mod, "_normalize_experiment_a", return_value=([], [])),
        patch.object(mod, "_normalize_experiment_d", return_value=([], [])),
        patch.object(mod, "_write_reports"),
        patch.object(
            mod,
            "_write_artifact_index",
            return_value="runs/r1/reports/artifact_index.json",
        ),
        patch.object(mod.projection, "mark_running"),
        patch.object(mod.projection, "finalize") as finalize,
        patch.object(mod, "_emit_finalize_metrics") as emit_metrics,
    ):
        res = mod.handler({"run_id": "123e4567-e89b-42d3-a456-426614174000"}, context)

    assert res["ok"] is True
    assert res["state"] == "SUCCEEDED"
    assert context.child_contexts == ["study1", "study2", "experiment_a", "experiment_d"]
    assert len(context.wait_configs) == 4
    finalize.assert_called_once()
    assert finalize.call_args.kwargs["state"] == "SUCCEEDED"
    emit_metrics.assert_called_once()


def test_experiment_a_predict_submit_runs_once_across_durable_replay(mod):
    class ReplayContext:
        def __init__(self):
            self.step_results = {}
            self.wait_counts = {"experiment_a_edit": 0, "experiment_a_predict": 0}

        def step(self, func, name):
            if name not in self.step_results:
                self.step_results[name] = func()
            return self.step_results[name]

        def run_in_child_context(self, func, name):
            return func(self)

        def wait_for_condition(self, config):
            phase_key = config.initial_state["phase_key"]
            self.wait_counts[phase_key] = self.wait_counts.get(phase_key, 0) + 1
            if phase_key == "experiment_a_predict" and self.wait_counts[phase_key] == 1:
                raise mod.WorkflowDeferred(phase="EXPERIMENT_A", step="EXPERIMENT_A_WAIT")
            return {"done": True}

    context = ReplayContext()
    run_id = "123e4567-e89b-42d3-a456-426614174019"

    with (
        patch.object(
            mod,
            "_load_config",
            return_value={
                "poll_interval_sec": 10,
                "models": ["apac.amazon.nova-micro-v1:0"],
                "shard_size": 500,
            },
        ),
        patch.object(
            mod,
            "_prepare_experiment_a",
            return_value={"manifest_count": 1, "seed_invalid_key": "runs/tmp/seed.jsonl"},
        ) as prepare_experiment_a,
        patch.object(
            mod,
            "_submit_experiment_a_prediction_jobs",
            return_value={"manifest_count": 2, "edit_invalid_key": "runs/tmp/edit.jsonl"},
        ) as submit_predict,
        patch.object(mod, "_normalize_experiment_a", return_value=([], [])),
        patch.object(mod.projection, "mark_running"),
    ):
        with pytest.raises(mod.WorkflowDeferred):
            mod._run_experiment_a_workflow(
                context,
                run_id,
                "trace-1",
                mod._initial_workflow_state(),
            )

        mod._run_experiment_a_workflow(
            context,
            run_id,
            "trace-1",
            mod._initial_workflow_state(),
        )

    assert prepare_experiment_a.call_count == 1
    assert submit_predict.call_count == 1


def test_run_child_context_falls_back_to_legacy_signature(mod):
    class LegacyContext:
        def __init__(self):
            self.child_contexts = []

        def run_in_child_context(self, name, func):
            self.child_contexts.append(name)
            return func(self)

    context = LegacyContext()

    result = mod._run_child_context(context, "study1", lambda child_context: child_context)

    assert result is context
    assert context.child_contexts[-1] == "study1"


def test_run_durable_step_supports_legacy_name_first_signature(mod):
    class LegacyContext:
        def __init__(self):
            self.steps = []

        def step(self, name, func):
            self.steps.append(name)
            return func()

    context = LegacyContext()

    result = mod._run_durable_step(context, "STUDY1_ENUMERATE", lambda: 7)

    assert result == 7
    assert context.steps == ["STUDY1_ENUMERATE"]


def test_run_durable_step_ignores_sdk_step_context_for_zero_arg_callable(mod):
    class SdkStyleContext:
        def __init__(self):
            self.steps = []

        def step(self, func, name):
            self.steps.append(name)
            return func({"attempt": 1})

    context = SdkStyleContext()

    result = mod._run_durable_step(context, "STUDY1_ENUMERATE", lambda: 7)

    assert result == 7
    assert context.steps == ["STUDY1_ENUMERATE"]


def test_handler_finalizes_partial_when_invalid_exists(mod):
    def seed_invalid(*_args, **_kwargs):
        pass

    def run_study1(_context, _run_id, _trace_id, state):
        state["invalid_counts"]["study1"] = 1

    with (
        patch.object(mod, "_load_config", return_value={}),
        patch.object(mod, "_run_study1", side_effect=run_study1),
        patch.object(mod, "_run_study2", side_effect=seed_invalid),
        patch.object(mod, "_run_experiment_a_workflow", side_effect=seed_invalid),
        patch.object(mod, "_run_experiment_d_workflow", side_effect=seed_invalid),
        patch.object(mod, "_run_report", side_effect=seed_invalid),
        patch.object(mod.projection, "finalize") as finalize,
        patch.object(mod, "_emit_finalize_metrics") as emit_metrics,
    ):
        res = mod.handler({"run_id": "123e4567-e89b-42d3-a456-426614174000"}, None)

    assert res["ok"] is True
    assert res["state"] == "PARTIAL"
    assert finalize.call_args.kwargs["state"] == "PARTIAL"
    emit_metrics.assert_called_once()


def test_handler_returns_pipeline_error_model(mod):
    err = mod.PipelineError(
        step="STUDY1_WAIT",
        reason="poll timeout",
        retryable=True,
        category="timeout",
    )
    with (
        patch.object(mod, "_load_config", return_value={}),
        patch.object(mod, "_run_study1", side_effect=err),
        patch.object(mod.projection, "finalize") as finalize,
        patch.object(mod, "_emit_finalize_metrics") as emit_metrics,
    ):
        res = mod.handler({"run_id": "123e4567-e89b-42d3-a456-426614174000"}, None)

    assert res["ok"] is False
    assert res["category"] == "timeout"
    assert res["retryable"] is True
    assert finalize.call_args.kwargs["last_error"]["step"] == "STUDY1_WAIT"
    assert emit_metrics.call_args.args[1] == "FAILED"


def test_handler_runs_repair_workflow_without_downstream_rebuild(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174030"
    repair_config = {
        "parent_run_id": "123e4567-e89b-42d3-a456-426614174000",
        "repair_phase": "study1",
        "repair_scope": "invalid_only",
        "repair_mode": "rerun",
        "rebuild_downstream": False,
    }

    with (
        patch.object(mod, "_load_config", return_value=repair_config),
        patch.object(mod, "_run_repair_study1") as run_repair,
        patch.object(mod, "_run_study2") as run_study2,
        patch.object(mod, "_run_experiment_a_workflow") as run_experiment_a,
        patch.object(mod, "_run_experiment_d_workflow") as run_experiment_d,
        patch.object(mod, "_run_report") as run_report,
        patch.object(mod.projection, "finalize") as finalize,
        patch.object(mod, "_emit_finalize_metrics") as emit_metrics,
    ):
        res = mod.handler({"run_id": run_id}, None)

    assert res["ok"] is True
    run_repair.assert_called_once()
    run_study2.assert_not_called()
    run_experiment_a.assert_not_called()
    run_experiment_d.assert_not_called()
    run_report.assert_called_once()
    assert finalize.call_args.kwargs["state"] == "SUCCEEDED"
    emit_metrics.assert_called_once()


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
