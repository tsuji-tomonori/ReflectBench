import importlib
import json
import os
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def mod():
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
    os.environ.setdefault("TABLE_NAME", "run_control_table")
    os.environ.setdefault("TABLE_GSI_NAME", "idempotency_key_index")
    os.environ.setdefault("ARTIFACTS_BUCKET", "dummy-bucket")
    os.environ.setdefault(
        "ORCHESTRATOR_ARN",
        "arn:aws:lambda:ap-southeast-2:123:function:orchestrator",
    )
    return importlib.import_module("app.start_run.handler")


def _event(body: dict) -> dict:
    return {"body": json.dumps(body)}


def test_returns_400_when_constraints_invalid(mod):
    res = mod.handler(_event({"loops": 9, "full_cross": True}), None)
    assert res["statusCode"] == 400


def test_returns_400_when_body_is_not_object(mod):
    res = mod.handler({"body": "[]"}, None)
    assert res["statusCode"] == 400


def test_returns_existing_run_id_on_idempotent_retry(mod):
    body = {
        "loops": 10,
        "full_cross": True,
        "idempotency_key": "k1",
    }

    with patch.object(
        mod,
        "_query_by_idempotency_key",
        return_value={
            "run_id": {"S": "run-123"},
            "request_hash": {"S": mod._request_hash(body)},
        },
    ):
        res = mod.handler(_event(body), None)

    payload = json.loads(res["body"])
    assert res["statusCode"] == 202
    assert payload["run_id"] == "run-123"


def test_returns_409_when_same_key_different_payload(mod):
    body = {
        "loops": 10,
        "full_cross": True,
        "idempotency_key": "k1",
        "poll_interval_sec": 120,
    }

    with patch.object(
        mod,
        "_query_by_idempotency_key",
        return_value={
            "run_id": {"S": "run-123"},
            "request_hash": {"S": "different-hash"},
        },
    ):
        res = mod.handler(_event(body), None)

    assert res["statusCode"] == 409
