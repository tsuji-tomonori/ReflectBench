import importlib
import json
import os
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def mod():
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
    os.environ.setdefault("ARTIFACTS_BUCKET", "dummy-bucket")
    return importlib.import_module("app.artifacts.handler")


def test_returns_400_when_run_id_missing(mod):
    res = mod.handler({"pathParameters": {}}, None)
    assert res["statusCode"] == 400


def test_returns_grouped_artifact_keys(mod):
    with patch.object(
        mod,
        "_list_keys",
        side_effect=[
            ["runs/run-1/reports/run_manifest.json"],
            ["runs/run-1/normalized/study1/part-00001.jsonl"],
            [],
        ],
    ):
        res = mod.handler({"pathParameters": {"run_id": "run-1"}}, None)

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert len(body["reports"]) == 1
    assert len(body["normalized"]) == 1
    assert len(body["invalid"]) == 0


def test_returns_empty_arrays_when_artifacts_not_generated(mod):
    with patch.object(mod, "_list_keys", side_effect=[[], [], []]):
        res = mod.handler({"pathParameters": {"run_id": "run-empty"}}, None)

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["reports"] == []
    assert body["normalized"] == []
    assert body["invalid"] == []
