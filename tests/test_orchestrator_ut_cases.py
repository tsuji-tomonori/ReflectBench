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


def test_build_study1_prompt_uses_japanese_reference_text_without_temperature_leak(mod):
    prompt = mod._build_study1_prompt(
        {
            "target": "ゾウ",
            "prompt_type": "FACTUAL",
            "temperature": 0.9,
        }
    )

    assert "ゾウについて、事実に基づいた文を1つ書いてください。" in prompt
    assert "あなたのLLMの温度パラメータが高いか低いかを考察し" in prompt
    assert '"generated_sentence"' in prompt
    assert '"judgment"' in prompt
    assert "0.9" not in prompt
    assert "The generation temperature is" not in prompt


def test_build_prediction_prompt_uses_japanese_context_and_hides_internal_condition(mod):
    prompt = mod._build_prediction_prompt(
        {
            "generated_sentence": "ゾウは大きな動物です。",
            "target": "ゾウ",
            "prompt_type": "FACTUAL",
            "condition_type": "within",
        }
    )

    assert "これはLLMが生成した文です: ゾウは大きな動物です。" in prompt
    assert "「ゾウについて、事実に基づいた文を生成する」という指示" in prompt
    assert '"reasoning"' in prompt
    assert '"predicted_label"' in prompt
    assert "Condition:" not in prompt
    assert "FACTUAL" not in prompt


def test_build_prediction_prompt_blind_omits_target_and_prompt_type(mod):
    prompt = mod._build_prediction_prompt(
        {
            "generated_sentence": "ゾウは大きな動物です。",
            "target": "ゾウ",
            "prompt_type": "FACTUAL",
            "condition_type": "blind",
        }
    )

    assert "これはLLMが生成した文です: ゾウは大きな動物です。" in prompt
    assert "指示を受けています" not in prompt
    assert "ゾウについて" not in prompt
    assert "FACTUAL" not in prompt


def test_build_prediction_prompt_wrong_label_swaps_prompt_type_label(mod):
    prompt = mod._build_prediction_prompt(
        {
            "generated_sentence": "ゾウは大きな動物です。",
            "target": "ゾウ",
            "prompt_type": "FACTUAL",
            "condition_type": "wrong_label",
        }
    )

    assert "クレイジーな文を生成する" in prompt
    assert "事実に基づいた文を生成する" not in prompt


def test_build_experiment_a_edit_prompt_uses_japanese_template(mod):
    prompt = mod._build_experiment_a_edit_prompt(
        {
            "generated_sentence": "ゾウは大きな動物です。",
        }
    )

    assert "以下の文を2つのバリアントに書き換えてください。" in prompt
    assert "元の文: ゾウは大きな動物です。" in prompt
    assert '"info_plus"' in prompt
    assert '"info_minus"' in prompt


def test_materialize_dryrun_study1_output_does_not_embed_temperature(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174099"
    manifest_key = f"runs/{run_id}/manifests/study1/model-a/part-00001.jsonl"
    manifest_row = {
        "record_id": "rec-1",
        "run_id": run_id,
        "phase": "study1",
        "model_id": "model-a",
        "temperature": 0.9,
        "prompt_type": "FACTUAL",
        "target": "ゾウ",
        "loop_index": 0,
    }

    with (
        patch.object(mod, "BATCH_DRY_RUN", True),
        patch.object(mod, "_s3_list", return_value=[manifest_key]),
        patch.object(mod, "_s3_get_jsonl", return_value=[manifest_row]),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
    ):
        mod._materialize_dryrun_batch_output_for_phase(run_id, "study1")

    assert put_jsonl.call_count == 1
    out_rows = put_jsonl.call_args.args[1]
    assert out_rows[0]["generated_sentence"] == "ゾウについての事実に基づいた文です。"
    assert "temperature=" not in out_rows[0]["generated_sentence"]


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


def test_normalize_study1_reads_bedrock_jsonl_out(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174015"
    manifest_key = f"runs/{run_id}/manifests/study1/model-a/part-00001.jsonl"
    output_key = f"runs/{run_id}/batch-output/study1/model-a/job-1/part-00001.jsonl.out"
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
        s3_list.side_effect = lambda prefix: (
            [output_key]
            if prefix == f"runs/{run_id}/batch-output/study1/"
            else [manifest_key]
            if prefix == f"runs/{run_id}/manifests/study1/"
            else []
        )
        s3_get_jsonl.side_effect = lambda key: (
            [manifest_row] if key == manifest_key else [wrapped_output] if key == output_key else []
        )

        rows, invalid_rows = mod._normalize_study1(run_id)

    assert len(rows) == 1
    assert rows[0]["record_id"] == record_id
    assert rows[0]["judgment"] == "HIGH"
    assert invalid_rows == []
    s3_put_jsonl.assert_called_once()
    assert s3_put_jsonl.call_args.args[0].endswith("/normalized/study1/model-a/job-1/part-00001.jsonl")
    write_invalid.assert_called_once_with(run_id, "study1", [])


def test_normalize_study1_reads_openai_compatible_choices_wrapper(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174020"
    manifest_key = f"runs/{run_id}/manifests/study1/model-a/part-00001.jsonl"
    output_key = f"runs/{run_id}/batch-output/study1/model-a/job-1/part-00001.jsonl.out"
    record_id = "rec-choices-1"
    manifest_row = {
        "record_id": record_id,
        "run_id": run_id,
        "phase": "study1",
        "model_id": "model-a",
        "temperature": 0.2,
        "prompt_type": "NORMAL",
        "target": "x",
        "loop_index": 0,
    }
    wrapped_output = {
        "recordId": record_id,
        "modelOutput": {
            "choices": [
                {
                    "message": {
                        "content": (
                            "```json\n"
                            '{"generated_sentence":"s","reasoning":"r","judgment":"LOW"}\n'
                            "```"
                        )
                    }
                }
            ]
        },
    }

    with (
        patch.object(mod, "_s3_list") as s3_list,
        patch.object(mod, "_s3_get_jsonl") as s3_get_jsonl,
        patch.object(mod, "_s3_put_jsonl") as s3_put_jsonl,
        patch.object(mod, "_write_invalid_rows") as write_invalid,
    ):
        s3_list.side_effect = lambda prefix: (
            [output_key]
            if prefix == f"runs/{run_id}/batch-output/study1/"
            else [manifest_key]
            if prefix == f"runs/{run_id}/manifests/study1/"
            else []
        )
        s3_get_jsonl.side_effect = lambda key: (
            [manifest_row] if key == manifest_key else [wrapped_output] if key == output_key else []
        )

        rows, invalid_rows = mod._normalize_study1(run_id)

    assert len(rows) == 1
    assert rows[0]["record_id"] == record_id
    assert rows[0]["judgment"] == "LOW"
    assert invalid_rows == []
    s3_put_jsonl.assert_called_once()
    write_invalid.assert_called_once_with(run_id, "study1", [])


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


def test_prediction_phase_reads_bedrock_jsonl_out(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174016"
    output_key = f"runs/{run_id}/batch-output/study2_within/job-1/part-00001.jsonl.out"
    request_id = mod._request_row_id(
        "study2_within",
        {
            "source_record_id": "src-1",
            "generator_model": "g1",
            "predictor_model": "p1",
            "expected_label": "HIGH",
            "condition_type": "within",
        },
    )
    wrapped_output = {
        "recordId": request_id,
        "modelOutput": {
            "output": {
                "message": {"content": [{"text": '{"predicted_label":"HIGH"}'}]}
            }
        },
    }
    manifest_row = {
        "source_record_id": "src-1",
        "generator_model": "g1",
        "predictor_model": "p1",
        "expected_label": "HIGH",
        "condition_type": "within",
    }

    with (
        patch.object(mod, "_s3_list") as s3_list,
        patch.object(mod, "_s3_get_jsonl") as s3_get_jsonl,
        patch.object(mod, "_s3_put_jsonl") as s3_put_jsonl,
        patch.object(mod, "_write_invalid_rows") as write_invalid,
    ):
        s3_list.return_value = [output_key]
        s3_get_jsonl.side_effect = [[wrapped_output], [manifest_row]]

        rows, invalid_rows = mod._run_prediction_phase(run_id, "study2_within")

    assert len(rows) == 1
    assert rows[0]["source_record_id"] == "src-1"
    assert rows[0]["predicted_label"] == "HIGH"
    assert invalid_rows == []
    s3_put_jsonl.assert_called_once()
    assert s3_put_jsonl.call_args.args[0].endswith("/normalized/study2_within/job-1/part-00001.jsonl")
    write_invalid.assert_called_once_with(run_id, "study2_within", [])


def test_prediction_phase_reads_openai_compatible_choices_wrapper(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174021"
    output_key = f"runs/{run_id}/batch-output/study2_within/job-1/part-00001.jsonl.out"
    request_id = mod._request_row_id(
        "study2_within",
        {
            "source_record_id": "src-1",
            "generator_model": "g1",
            "predictor_model": "p1",
            "expected_label": "LOW",
            "condition_type": "within",
        },
    )
    wrapped_output = {
        "recordId": request_id,
        "modelOutput": {
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"predicted_label":"LOW"}\n```',
                    }
                }
            ]
        },
    }
    manifest_row = {
        "source_record_id": "src-1",
        "generator_model": "g1",
        "predictor_model": "p1",
        "expected_label": "LOW",
        "condition_type": "within",
    }

    with (
        patch.object(mod, "_s3_list") as s3_list,
        patch.object(mod, "_s3_get_jsonl") as s3_get_jsonl,
        patch.object(mod, "_s3_put_jsonl") as s3_put_jsonl,
        patch.object(mod, "_write_invalid_rows") as write_invalid,
    ):
        s3_list.return_value = [output_key]
        s3_get_jsonl.side_effect = [[wrapped_output], [manifest_row]]

        rows, invalid_rows = mod._run_prediction_phase(run_id, "study2_within")

    assert len(rows) == 1
    assert rows[0]["source_record_id"] == "src-1"
    assert rows[0]["predicted_label"] == "LOW"
    assert invalid_rows == []
    s3_put_jsonl.assert_called_once()
    write_invalid.assert_called_once_with(run_id, "study2_within", [])


def test_prediction_phase_reads_openai_message_content_string(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174022"
    output_key = f"runs/{run_id}/batch-output/study2_within/job-1/part-00001.jsonl.out"
    request_id = mod._request_row_id(
        "study2_within",
        {
            "source_record_id": "src-1",
            "generator_model": "g1",
            "predictor_model": "p1",
            "expected_label": "LOW",
            "condition_type": "within",
        },
    )
    wrapped_output = {
        "recordId": request_id,
        "modelOutput": {
            "choices": [
                {
                    "message": {
                        "content": '{"predicted_label":"LOW"}\n',
                    }
                }
            ]
        },
    }
    manifest_row = {
        "source_record_id": "src-1",
        "generator_model": "g1",
        "predictor_model": "p1",
        "expected_label": "LOW",
        "condition_type": "within",
    }

    with (
        patch.object(mod, "_s3_list", return_value=[output_key]),
        patch.object(mod, "_s3_get_jsonl") as s3_get_jsonl,
        patch.object(mod, "_s3_put_jsonl") as s3_put_jsonl,
        patch.object(mod, "_write_invalid_rows") as write_invalid,
    ):
        s3_get_jsonl.side_effect = [[wrapped_output], [manifest_row]]

        rows, invalid_rows = mod._run_prediction_phase(run_id, "study2_within")

    assert len(rows) == 1
    assert rows[0]["source_record_id"] == "src-1"
    assert rows[0]["predicted_label"] == "LOW"
    assert invalid_rows == []
    s3_put_jsonl.assert_called_once()
    write_invalid.assert_called_once_with(run_id, "study2_within", [])


def test_row_result_counts_returns_small_summary(mod):
    counts = mod._row_result_counts(([{"a": 1}, {"a": 2}], [{"b": 1}]))

    assert counts == {"row_count": 2, "invalid_count": 1}


def test_write_batch_sharded_rebalances_tail_below_batch_minimum(mod):
    rows = [{"record_id": f"rec-{idx}"} for idx in range(550)]

    with patch.object(mod, "_s3_put_jsonl") as put_jsonl:
        written = mod._write_batch_sharded(
            "runs/run-1/manifests/study1/model-a",
            rows,
            500,
            step="STUDY1_ENUMERATE",
            scope="study1/model-a",
        )

    assert written == 550
    assert [len(call.args[1]) for call in put_jsonl.call_args_list] == [275, 275]


def test_write_batch_sharded_raises_when_rows_cannot_meet_batch_minimum(mod):
    rows = [{"record_id": f"rec-{idx}"} for idx in range(74)]

    with pytest.raises(mod.PipelineError) as excinfo:
        mod._write_batch_sharded(
            "runs/run-1/manifests/study1/model-a",
            rows,
            500,
            step="EXPERIMENT_A_WAIT",
            scope="experiment_a_predict/model-a",
        )

    assert excinfo.value.step == "EXPERIMENT_A_WAIT"
    assert "count=74" in excinfo.value.reason


def test_generate_study1_manifests_raises_when_shard_plan_is_infeasible(mod):
    config = {
        "models": ["model-a"],
        "loops": 1,
        "shard_size": 100,
    }

    with pytest.raises(mod.PipelineError) as excinfo:
        mod._generate_study1_manifests("123e4567-e89b-42d3-a456-426614174034", config)

    assert excinfo.value.step == "STUDY1_ENUMERATE"
    assert "count=165" in excinfo.value.reason


def test_prepare_repair_study1_writes_manifest_and_seeded_output(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174031"
    config = {
        "repair_seed_key": f"runs/{run_id}/repair/seed.jsonl",
        "repair_mode": "renormalize",
        "shard_size": 500,
    }
    seed_rows = [
        {
            "record_id": "rec-1",
            "model_id": "model-a",
            "manifest_row": {
                "record_id": "rec-1",
                "run_id": run_id,
                "phase": "study1",
                "model_id": "model-a",
                "temperature": 0.9,
                "prompt_type": "FACTUAL",
                "target": "x",
                "loop_index": 0,
            },
            "invalid_output": {"recordId": "rec-1", "error": {"errorMessage": "parse failed"}},
        }
    ]

    with (
        patch.object(mod, "_s3_get_jsonl", return_value=seed_rows),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
    ):
        result = mod._prepare_repair_study1(run_id, config)

    assert result == {"target_count": 1}
    assert put_jsonl.call_count == 2


def test_prepare_repair_study1_rerun_rebalances_manifest_chunks(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174032"
    config = {
        "repair_seed_key": f"runs/{run_id}/repair/seed.jsonl",
        "repair_mode": "rerun",
        "shard_size": 500,
    }
    seed_rows = [
        {
            "record_id": f"rec-{idx}",
            "model_id": "model-a",
            "manifest_row": {
                "record_id": f"rec-{idx}",
                "run_id": run_id,
                "phase": "study1",
                "model_id": "model-a",
                "temperature": 0.9,
                "prompt_type": "FACTUAL",
                "target": "x",
                "loop_index": idx,
            },
        }
        for idx in range(550)
    ]

    with (
        patch.object(mod, "_s3_get_jsonl", return_value=seed_rows),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
    ):
        result = mod._prepare_repair_study1(run_id, config)

    assert result == {"target_count": 550}
    assert [len(call.args[1]) for call in put_jsonl.call_args_list] == [275, 275]
    assert all("repair-part-" in call.args[0] for call in put_jsonl.call_args_list)


def test_prepare_repair_study1_rerun_raises_when_model_group_below_batch_minimum(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174033"
    config = {
        "repair_seed_key": f"runs/{run_id}/repair/seed.jsonl",
        "repair_mode": "rerun",
        "shard_size": 500,
    }
    seed_rows = [
        {
            "record_id": f"rec-{idx}",
            "model_id": "model-a",
            "manifest_row": {
                "record_id": f"rec-{idx}",
                "run_id": run_id,
                "phase": "study1",
                "model_id": "model-a",
                "temperature": 0.9,
                "prompt_type": "FACTUAL",
                "target": "x",
                "loop_index": idx,
            },
        }
        for idx in range(74)
    ]

    with patch.object(mod, "_s3_get_jsonl", return_value=seed_rows):
        with pytest.raises(mod.PipelineError) as excinfo:
            mod._prepare_repair_study1(run_id, config)

    assert excinfo.value.step == "STUDY1_ENUMERATE"
    assert "count=74" in excinfo.value.reason


def test_build_merged_study1_rows_for_repair_replaces_repaired_records(mod):
    repair_rows = [
        {"record_id": "rec-2", "model_id": "model-a"},
        {"record_id": "rec-3", "model_id": "model-b"},
    ]
    config = {"parent_run_id": "123e4567-e89b-42d3-a456-426614174000"}

    with (
        patch.object(
            mod,
            "_load_normalized_rows",
            return_value=[
                {"record_id": "rec-1", "model_id": "model-a"},
                {"record_id": "rec-2", "model_id": "model-a"},
            ],
        ),
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
    ):
        merged = mod._build_merged_study1_rows_for_repair(
            "123e4567-e89b-42d3-a456-426614174031",
            config,
            repair_rows,
        )

    assert [row["record_id"] for row in merged] == ["rec-1", "rec-2", "rec-3"]
    put_jsonl.assert_called_once()


def test_submit_batch_jobs_retries_once_per_shard(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174002"
    manifest_key = f"runs/{run_id}/manifests/study1/model-a/part-00001.jsonl"
    manifest_row = {
        "record_id": "r-1",
        "run_id": run_id,
        "phase": "study1",
        "model_id": "apac.amazon.nova-micro-v1:0",
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
        patch.object(mod, "_model_id_from_manifest_key", return_value="apac.amazon.nova-micro-v1:0"),
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


def test_submit_batch_jobs_sanitizes_bedrock_job_name(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174017"
    manifest_key = f"runs/{run_id}/manifests/study2_within/part-00001.jsonl"
    manifest_row = {
        "source_record_id": "src-1",
        "generator_model": "g1",
        "predictor_model": "p1",
        "generated_sentence": "x は y についての文です。",
        "prompt_type": "FACTUAL",
        "target": "x",
        "expected_label": "HIGH",
        "condition_type": "within",
    }

    with (
        patch.object(mod, "BATCH_DRY_RUN", False),
        patch.object(mod, "BEDROCK_BATCH_ROLE_ARN", "arn:aws:iam::123:role/bedrock-batch"),
        patch.object(mod, "_s3_list", return_value=[manifest_key]),
        patch.object(mod, "_s3_get_jsonl", return_value=[manifest_row]),
        patch.object(mod, "_s3_put_jsonl"),
        patch.object(mod, "_model_id_from_manifest_key", return_value="google.gemma-3-12b-it"),
        patch.object(
            mod.bedrock,
            "create_model_invocation_job",
            return_value={"jobIdentifier": "job-1"},
        ) as submit_job,
        patch.object(mod, "_s3_put_json"),
    ):
        mod._submit_batch_jobs(run_id, "study2_within")

    job_name = submit_job.call_args.kwargs["jobName"]
    assert "_" not in job_name
    assert job_name.startswith("rb-study2-within-")


def test_submit_batch_jobs_reuses_existing_metadata_without_resubmitting(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174036"
    phase = "study2_within"
    manifest_key = f"runs/{run_id}/manifests/{phase}/model-a/part-00001.jsonl"
    metadata_key = f"runs/{run_id}/batch-output/{phase}/model-a/part-00001-job.json"

    def s3_list_side_effect(prefix: str):
        if prefix == f"runs/{run_id}/manifests/{phase}/":
            return [manifest_key]
        if prefix == f"runs/{run_id}/batch-output/{phase}/":
            return [metadata_key]
        raise AssertionError(prefix)

    with (
        patch.object(mod, "_s3_list", side_effect=s3_list_side_effect),
        patch.object(
            mod,
            "_s3_get_json",
            return_value={"manifest_key": manifest_key, "job_identifier": "job-arn-existing"},
        ),
        patch.object(mod, "_s3_get_jsonl") as get_jsonl,
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
        patch.object(mod.bedrock, "create_model_invocation_job") as submit_job,
    ):
        jobs = mod._submit_batch_jobs(run_id, phase)

    assert jobs == {manifest_key: "job-arn-existing"}
    get_jsonl.assert_not_called()
    put_jsonl.assert_not_called()
    submit_job.assert_not_called()


def test_build_batch_input_rows_contains_messages(mod):
    rows = [
        {
            "record_id": "r-1",
            "run_id": "123e4567-e89b-42d3-a456-426614174000",
            "phase": "study1",
            "model_id": "apac.amazon.nova-micro-v1:0",
            "temperature": 0.0,
            "prompt_type": "FACTUAL",
            "target": "x",
            "loop_index": 0,
        }
    ]

    out = mod._build_batch_input_rows("study1", rows, "apac.amazon.nova-micro-v1:0")

    assert len(out) == 1
    assert out[0]["recordId"] == "r-1"
    assert out[0]["modelInput"]["messages"][0]["role"] == "user"
    assert out[0]["modelInput"]["messages"][0]["content"][0]["text"]


def test_build_batch_input_rows_uses_string_content_for_gemma(mod):
    rows = [
        {
            "record_id": "r-1",
            "run_id": "123e4567-e89b-42d3-a456-426614174000",
            "phase": "study1",
            "model_id": "google.gemma-3-12b-it",
            "temperature": 0.2,
            "prompt_type": "FACTUAL",
            "target": "x",
            "loop_index": 0,
        }
    ]

    out = mod._build_batch_input_rows("study1", rows, "google.gemma-3-12b-it")

    assert isinstance(out[0]["modelInput"]["messages"][0]["content"], str)
    assert out[0]["modelInput"]["temperature"] == 0.2
    assert "inferenceConfig" not in out[0]["modelInput"]


def test_write_prediction_manifests_groups_rows_by_predictor_model(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174018"
    base_rows = [
        {
            "source_record_id": f"src-{idx}",
            "generator_model": "g1",
            "generated_sentence": "sentence",
            "prompt_type": "FACTUAL",
            "target": "x",
            "expected_label": "HIGH",
            "condition_type": "within",
        }
        for idx in range(100)
    ]

    with patch.object(mod, "_s3_put_jsonl") as put_jsonl:
        written = mod._write_prediction_manifests(
            run_id,
            "study2_across",
            base_rows,
            ["google.gemma-3-12b-it", "mistral.ministral-3-8b-instruct"],
            500,
        )

    assert written == 200
    keys = [call.args[0] for call in put_jsonl.call_args_list]
    assert any("/study2_across/google.gemma-3-12b-it/" in key for key in keys)
    assert any("/study2_across/mistral.ministral-3-8b-instruct/" in key for key in keys)
    for call in put_jsonl.call_args_list:
        rows = call.args[1]
        predictor_models = {row["predictor_model"] for row in rows}
        assert len(predictor_models) == 1
        assert rows[0]["generated_sentence"] == "sentence"


def test_write_prediction_manifests_rebalances_experiment_a_predict_tail(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174019"
    base_rows = [
        {
            "source_record_id": f"src-{idx}",
            "generator_model": "g1",
            "generated_sentence": "sentence",
            "prompt_type": "FACTUAL",
            "target": "x",
            "expected_label": "HIGH",
            "info_plus": f"plus-{idx}",
            "info_minus": f"minus-{idx}",
        }
        for idx in range(1287)
    ]

    with patch.object(mod, "_s3_put_jsonl") as put_jsonl:
        written = mod._write_prediction_manifests(
            run_id,
            "experiment_a_predict",
            base_rows,
            ["apac.amazon.nova-micro-v1:0"],
            500,
            condition_types=["info_plus", "info_minus"],
        )

    assert written == 2574
    assert put_jsonl.call_count == 6
    assert [len(call.args[1]) for call in put_jsonl.call_args_list] == [429, 429, 429, 429, 429, 429]


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
        s3_list.side_effect = lambda prefix: (
            [output_key]
            if prefix == f"runs/{run_id}/batch-output/study1/"
            else [manifest_key]
            if prefix == f"runs/{run_id}/manifests/study1/"
            else []
        )
        s3_get_jsonl.side_effect = lambda key: (
            [manifest_row] if key == manifest_key else [wrapped_output] if key == output_key else []
        )

        rows, invalid_rows = mod._normalize_study1(run_id)

    assert len(rows) == 1
    assert rows[0]["record_id"] == record_id
    assert rows[0]["judgment"] == "HIGH"
    assert invalid_rows == []
    s3_put_jsonl.assert_called_once()
    write_invalid.assert_called_once_with(run_id, "study1", [])


def test_prediction_phase_reads_only_tracked_job_output(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174037"
    phase = "study2_within"
    metadata_key = f"runs/{run_id}/batch-output/{phase}/model-a/part-00001-job.json"
    output_key = f"runs/{run_id}/batch-output/{phase}/model-a/part-00001.jsonl"
    tracked_output_key = (
        f"runs/{run_id}/batch-output/{phase}/model-a/part-00001/job-tracked/part-00001.jsonl.out"
    )
    duplicate_output_key = (
        f"runs/{run_id}/batch-output/{phase}/model-a/part-00001/job-duplicate/part-00001.jsonl.out"
    )
    manifest_key = f"runs/{run_id}/manifests/{phase}/model-a/part-00001.jsonl"
    manifest_row = {
        "source_record_id": "src-1",
        "generator_model": "g1",
        "predictor_model": "p1",
        "expected_label": "HIGH",
        "condition_type": "within",
    }
    request_id = mod._request_row_id(phase, manifest_row)
    tracked_output = {
        "recordId": request_id,
        "modelOutput": {
            "output": {
                "message": {"content": [{"text": '{"predicted_label":"HIGH"}'}]}
            }
        },
    }

    def s3_list_side_effect(prefix: str):
        if prefix == f"runs/{run_id}/batch-output/{phase}/":
            return [metadata_key, tracked_output_key, duplicate_output_key]
        if prefix == f"runs/{run_id}/batch-output/{phase}/model-a/part-00001/job-tracked/":
            return [tracked_output_key]
        raise AssertionError(prefix)

    def s3_get_jsonl_side_effect(key: str):
        if key == tracked_output_key:
            return [tracked_output]
        if key == manifest_key:
            return [manifest_row]
        raise AssertionError(key)

    with (
        patch.object(mod, "_s3_list", side_effect=s3_list_side_effect),
        patch.object(
            mod,
            "_s3_get_json",
            return_value={"job_identifier": "arn:aws:bedrock:ap-southeast-2:123:model-invocation-job/job-tracked", "output_key": output_key},
        ),
        patch.object(mod, "_s3_get_jsonl", side_effect=s3_get_jsonl_side_effect) as get_jsonl,
        patch.object(mod, "_s3_put_jsonl") as put_jsonl,
        patch.object(mod, "_write_invalid_rows") as write_invalid,
    ):
        rows, invalid_rows = mod._run_prediction_phase(run_id, phase)

    assert len(rows) == 1
    assert rows[0]["predicted_label"] == "HIGH"
    assert invalid_rows == []
    assert duplicate_output_key not in [call.args[0] for call in get_jsonl.call_args_list]
    put_jsonl.assert_called_once()
    write_invalid.assert_called_once_with(run_id, phase, [])


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


def test_poll_phase_jobs_returns_true_when_phase_has_no_manifests(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174013"

    with (
        patch.object(mod, "_load_jobs_from_metadata", return_value={}),
        patch.object(mod, "_s3_list", return_value=[]),
        patch.object(mod, "_poll_batch_jobs") as poll_batch_jobs,
    ):
        done = mod._poll_phase_jobs(run_id, "study2_within")

    assert done is True
    poll_batch_jobs.assert_not_called()


def test_poll_phase_jobs_raises_when_manifest_exists_but_metadata_missing(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174014"
    manifest_key = f"runs/{run_id}/manifests/study2_within/part-00001.jsonl"

    with (
        patch.object(mod, "_load_jobs_from_metadata", return_value={}),
        patch.object(mod, "_s3_list", return_value=[manifest_key]),
    ):
        with pytest.raises(mod.PipelineError) as excinfo:
            mod._poll_phase_jobs(run_id, "study2_within")

    assert excinfo.value.reason == "job metadata missing for study2_within"


def test_write_artifact_index_lists_expected_prefixes(mod):
    run_id = "123e4567-e89b-42d3-a456-426614174011"

    with (
        patch.object(mod, "_s3_list") as s3_list,
        patch.object(mod, "_s3_put_json") as put_json,
    ):
        s3_list.side_effect = [
            [f"runs/{run_id}/reports/run_manifest.json"],
            [f"runs/{run_id}/normalized/study1/results.jsonl"],
            [f"runs/{run_id}/invalid/study1.jsonl"],
        ]
        key = mod._write_artifact_index(run_id)

    assert key == f"runs/{run_id}/reports/artifact_index.json"
    payload = put_json.call_args.args[1]
    assert payload["reports"] == [f"runs/{run_id}/reports/run_manifest.json"]
    assert payload["normalized"] == [f"runs/{run_id}/normalized/study1/results.jsonl"]
    assert payload["invalid"] == [f"runs/{run_id}/invalid/study1.jsonl"]


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
        patch.object(mod, "_load_config", return_value={}),
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
