from typing import Literal
from pydantic import field_validator

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_EDITOR_MODEL: Literal["apac.amazon.nova-micro-v1:0"] = "apac.amazon.nova-micro-v1:0"
ALL_MODELS = [
    "apac.amazon.nova-micro-v1:0",
    "google.gemma-3-12b-it",
    "mistral.ministral-3-8b-instruct",
    "qwen.qwen3-32b-v1:0",
]
DEFAULT_MODELS = [
    "apac.amazon.nova-micro-v1:0",
    "google.gemma-3-12b-it",
    "mistral.ministral-3-8b-instruct",
]
BATCH_UNSUPPORTED_MODELS = {
    "qwen.qwen3-32b-v1:0": "Bedrock batch inference only accepts InvokeModel/Converse bodies, but this model supports OpenAI Chat Completions only.",
}


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    loops: Literal[10]
    full_cross: Literal[True]
    shard_size: int = Field(default=500, ge=100)
    poll_interval_sec: int = Field(default=180, ge=60)
    editor_model: Literal["apac.amazon.nova-micro-v1:0"] = DEFAULT_EDITOR_MODEL
    models: list[str] | None = Field(default=None, min_length=1)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("models")
    @classmethod
    def validate_models(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        deduped = list(dict.fromkeys(value))
        unknown = sorted(set(deduped) - set(ALL_MODELS))
        if unknown:
            raise ValueError(f"unsupported models: {', '.join(unknown)}")
        batch_unsupported = [model for model in deduped if model in BATCH_UNSUPPORTED_MODELS]
        if batch_unsupported:
            details = "; ".join(
                f"{model}: {BATCH_UNSUPPORTED_MODELS[model]}" for model in batch_unsupported
            )
            raise ValueError(f"batch-unsupported models: {details}")
        return deduped


class RepairRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    phase: Literal["study1"]
    scope: Literal["invalid_only"]
    mode: Literal["renormalize", "rerun"]
    models: list[str] | None = Field(default=None, min_length=1)
    record_ids: list[str] | None = Field(default=None, min_length=1)
    rebuild_downstream: bool = False

    @field_validator("models")
    @classmethod
    def validate_models(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        deduped = list(dict.fromkeys(value))
        unknown = sorted(set(deduped) - set(ALL_MODELS))
        if unknown:
            raise ValueError(f"unsupported models: {', '.join(unknown)}")
        batch_unsupported = [model for model in deduped if model in BATCH_UNSUPPORTED_MODELS]
        if batch_unsupported:
            details = "; ".join(
                f"{model}: {BATCH_UNSUPPORTED_MODELS[model]}" for model in batch_unsupported
            )
            raise ValueError(f"batch-unsupported models: {details}")
        return deduped

    @field_validator("record_ids")
    @classmethod
    def validate_record_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        deduped = list(dict.fromkeys(value))
        if any(not record_id for record_id in deduped):
            raise ValueError("record_ids must not contain empty value")
        return deduped


class Study1BatchRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    record_id: str
    run_id: str
    phase: Literal["study1"]
    model_id: str
    temperature: float
    prompt_type: str
    target: str
    loop_index: int
    generated_sentence: str
    reasoning: str
    judgment: Literal["HIGH", "LOW"]


class PredictionBatchRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    source_record_id: str
    generator_model: str
    predictor_model: str
    expected_label: Literal["HIGH", "LOW"]
    condition_type: str
    predicted_label: Literal["HIGH", "LOW"]
