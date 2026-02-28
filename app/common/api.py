import json
import re
import uuid

RUN_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    flags=re.IGNORECASE,
)


def trace_id_from_event(event: dict) -> str:
    headers = event.get("headers") or {}
    for key in ("x-trace-id", "X-Trace-Id", "x-request-id", "X-Request-Id"):
        value = headers.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    request_context = event.get("requestContext") or {}
    request_id = request_context.get("requestId")
    if isinstance(request_id, str) and request_id.strip():
        return request_id.strip()

    return str(uuid.uuid4())


def problem_response(
    *,
    status_code: int,
    code: str,
    message: str,
    category: str,
    retryable: bool,
    step: str,
    trace_id: str,
    extra: dict | None = None,
) -> dict:
    body = {
        "code": code,
        "message": message,
        "category": category,
        "retryable": retryable,
        "step": step,
        "trace_id": trace_id,
    }
    if extra:
        body.update(extra)

    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/problem+json",
            "x-trace-id": trace_id,
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def json_response(status_code: int, body: dict, trace_id: str) -> dict:
    headers = {
        "content-type": "application/json",
        "x-trace-id": trace_id,
    }
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, ensure_ascii=False),
    }


def is_valid_run_id(value: str | None) -> bool:
    if not value:
        return False
    return RUN_ID_RE.fullmatch(value) is not None
