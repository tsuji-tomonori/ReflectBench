from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_EDITOR_MODEL: Literal["apac.amazon.nova-micro-v1:0"] = "apac.amazon.nova-micro-v1:0"
DEFAULT_MODELS = [
    "apac.amazon.nova-micro-v1:0",
    "google.gemma-3-12b-it",
    "mistral.ministral-3-8b-instruct",
    "qwen.qwen3-32b-v1:0",
]


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    loops: Literal[10]
    full_cross: Literal[True]
    shard_size: int = Field(default=500, ge=100)
    poll_interval_sec: int = Field(default=180, ge=60)
    editor_model: Literal["apac.amazon.nova-micro-v1:0"] = DEFAULT_EDITOR_MODEL
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)


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
