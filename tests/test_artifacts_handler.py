import importlib
import json
import os
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def mod():
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
    os.environ.setdefault("ARTIFACTS_BUCKET", "dummy-bucket")
    os.environ.setdefault("TABLE_NAME", "run_control_table")
    return importlib.import_module("app.artifacts.handler")


def test_returns_400_when_run_id_missing(mod):
    res = mod.handler({"pathParameters": {}}, None)
    assert res["statusCode"] == 400


def test_returns_grouped_artifact_keys(mod):
    with (
        patch.object(
            mod,
            "_run_exists",
            return_value=True,
        ),
        patch.object(
            mod,
            "_list_keys",
            side_effect=[
                ["runs/123e4567-e89b-42d3-a456-426614174000/reports/run_manifest.json"],
                ["runs/123e4567-e89b-42d3-a456-426614174000/normalized/study1/part-00001.jsonl"],
                [],
            ],
        ),
        patch.object(mod, "_load_run_item", return_value=None),
    ):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174000"}},
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert len(body["reports"]) == 1
    assert len(body["normalized"]) == 1
    assert len(body["invalid"]) == 0


def test_returns_empty_arrays_when_artifacts_not_generated(mod):
    with (
        patch.object(mod, "_run_exists", return_value=True),
        patch.object(mod, "_list_keys", side_effect=[[], [], []]),
        patch.object(mod, "_load_run_item", return_value=None),
    ):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174099"}},
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["reports"] == []
    assert body["normalized"] == []
    assert body["invalid"] == []


def test_returns_lineage_and_repair_metadata(mod):
    run_item = {
        "parent_run_id": {"S": "123e4567-e89b-42d3-a456-426614174000"},
        "repair_phase": {"S": "study1"},
        "repair_scope": {"S": "invalid_only"},
        "repair_mode": {"S": "renormalize"},
        "rebuild_downstream": {"BOOL": False},
        "source_invalid_keys": {
            "L": [
                {
                    "S": (
                        "runs/123e4567-e89b-42d3-a456-426614174000/"
                        "invalid/study1/model-a/invalid.jsonl"
                    )
                }
            ]
        },
    }

    with (
        patch.object(mod, "_run_exists", return_value=True),
        patch.object(mod, "_list_keys", side_effect=[[], [], []]),
        patch.object(mod, "_load_run_item", return_value=run_item),
    ):
        res = mod.handler(
            {"pathParameters": {"run_id": "123e4567-e89b-42d3-a456-426614174010"}},
            None,
        )

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["lineage"] == {
        "parent_run_id": "123e4567-e89b-42d3-a456-426614174000",
    }
    assert body["repair"] == {
        "phase": "study1",
        "scope": "invalid_only",
        "mode": "renormalize",
        "rebuild_downstream": False,
        "source_invalid_keys": [
            "runs/123e4567-e89b-42d3-a456-426614174000/invalid/study1/model-a/invalid.jsonl"
        ],
    }
