import importlib
import io
import json
import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(scope="module")
def mod():
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-2")
    os.environ.setdefault("TABLE_NAME", "run_control_table")
    os.environ.setdefault("ARTIFACTS_BUCKET", "dummy-bucket")
    return importlib.import_module("app.list_runs.handler")


def _scan_item(run_id: str, created_at: str, *, artifact_index_key: str | None = None) -> dict:
    item = {
        "run_id": {"S": run_id},
        "phase": {"S": "STUDY1"},
        "step": {"S": "STUDY1_WAIT"},
        "state": {"S": "RUNNING"},
        "created_at": {"S": created_at},
        "updated_at": {"S": created_at},
        "progress": {
            "M": {
                "completed_steps": {"N": "1"},
                "total_steps": {"N": "18"},
                "percent": {"N": "5"},
            }
        },
        "config_s3_key": {"S": f"runs/{run_id}/config.json"},
    }
    if artifact_index_key is not None:
        item["artifact_index_key"] = {"S": artifact_index_key}
    return item


def test_returns_400_for_invalid_limit(mod):
    res = mod.handler({"queryStringParameters": {"limit": "0"}}, None)
    assert res["statusCode"] == 400


def test_returns_400_for_invalid_next_token(mod):
    res = mod.handler({"queryStringParameters": {"next_token": "%%%"}}, None)
    assert res["statusCode"] == 400


def test_returns_runs_sorted_with_s3_status_and_next_token(mod):
    latest = _scan_item(
        "123e4567-e89b-42d3-a456-426614174002",
        "2026-03-06T00:00:00+00:00",
        artifact_index_key="runs/123e4567-e89b-42d3-a456-426614174002/reports/artifact_index.json",
    )
    older = _scan_item(
        "123e4567-e89b-42d3-a456-426614174001",
        "2026-03-05T00:00:00+00:00",
    )
    idempotency = {"run_id": {"S": "idempotency#k1"}, "kind": {"S": "IDEMPOTENCY"}}

    with (
        patch.object(mod.dynamodb, "scan", return_value={"Items": [older, idempotency, latest]}),
        patch.object(mod.s3, "head_object", return_value={}),
        patch.object(
            mod.s3,
            "get_object",
            return_value={
                "Body": io.BytesIO(
                    json.dumps(
                        {
                            "reports": [
                                "runs/123e4567-e89b-42d3-a456-426614174002/reports/run_manifest.json"
                            ],
                            "normalized": [
                                "runs/123e4567-e89b-42d3-a456-426614174002/normalized/study1/results.jsonl"
                            ],
                            "invalid": [],
                        }
                    ).encode("utf-8")
                )
            },
        ),
        patch.object(
            mod.s3,
            "list_objects_v2",
            return_value={
                "Contents": [
                    {
                        "Key": (
                            "runs/123e4567-e89b-42d3-a456-426614174002/"
                            "batch-output/study1/part-00001.jsonl"
                        ),
                        "LastModified": datetime(2026, 3, 6, tzinfo=UTC),
                    }
                ],
                "IsTruncated": False,
            },
        ),
    ):
        res = mod.handler({"queryStringParameters": {"limit": "1"}}, None)

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["returned_count"] == 1
    assert body["total_count"] == 2
    assert body["next_token"] is not None
    assert body["runs"][0]["run_id"] == "123e4567-e89b-42d3-a456-426614174002"
    assert body["runs"][0]["s3_status"]["config_exists"] is True
    assert body["runs"][0]["s3_status"]["artifact_index_exists"] is True
    assert body["runs"][0]["s3_status"]["reports"]["count"] == 1
    assert body["runs"][0]["s3_status"]["normalized"]["count"] == 1
    assert body["runs"][0]["s3_status"]["batch_output"]["count"] == 1


def test_falls_back_to_prefix_listing_when_artifact_index_is_missing(mod):
    item = _scan_item(
        "123e4567-e89b-42d3-a456-426614174003",
        "2026-03-04T00:00:00+00:00",
    )
    not_found = ClientError({"Error": {"Code": "404", "Message": "not found"}}, "HeadObject")

    with (
        patch.object(mod.dynamodb, "scan", return_value={"Items": [item]}),
        patch.object(mod.s3, "head_object", side_effect=not_found),
        patch.object(
            mod.s3,
            "list_objects_v2",
            side_effect=[
                {
                    "Contents": [
                        {
                            "Key": (
                                "runs/123e4567-e89b-42d3-a456-426614174003/"
                                "reports/run_manifest.json"
                            ),
                            "LastModified": datetime(2026, 3, 4, tzinfo=UTC),
                        }
                    ],
                    "IsTruncated": False,
                },
                {
                    "Contents": [],
                    "IsTruncated": False,
                },
                {
                    "Contents": [],
                    "IsTruncated": False,
                },
                {
                    "Contents": [
                        {
                            "Key": (
                                "runs/123e4567-e89b-42d3-a456-426614174003/"
                                "batch-output/study1/part-00001.jsonl"
                            ),
                            "LastModified": datetime(2026, 3, 4, tzinfo=UTC),
                        }
                    ],
                    "IsTruncated": False,
                },
            ],
        ),
    ):
        res = mod.handler({"queryStringParameters": {}}, None)

    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["runs"][0]["run_id"] == "123e4567-e89b-42d3-a456-426614174003"
    assert body["runs"][0]["s3_status"]["config_exists"] is False
    assert body["runs"][0]["s3_status"]["artifact_index_exists"] is False
    assert body["runs"][0]["s3_status"]["reports"]["count"] == 1
    assert body["runs"][0]["s3_status"]["batch_output"]["count"] == 1
