import math

BATCH_MIN_RECORDS = 100


def plan_batch_shards(total_rows: int, max_shard_size: int) -> list[int]:
    if total_rows < 0:
        raise ValueError("total_rows must be non-negative")
    if total_rows == 0:
        return []
    if max_shard_size < BATCH_MIN_RECORDS:
        raise ValueError(f"max_shard_size must be at least {BATCH_MIN_RECORDS}")

    min_shards = math.ceil(total_rows / max_shard_size)
    max_shards = total_rows // BATCH_MIN_RECORDS
    if min_shards > max_shards:
        raise ValueError(
            "count cannot be partitioned into Bedrock Batch shards with "
            f"min={BATCH_MIN_RECORDS} and max={max_shard_size}: count={total_rows}"
        )

    base_size, remainder = divmod(total_rows, min_shards)
    sizes = [base_size + (1 if idx < remainder else 0) for idx in range(min_shards)]
    if any(size < BATCH_MIN_RECORDS or size > max_shard_size for size in sizes):
        raise ValueError(
            "planned shard sizes violate Bedrock Batch constraints: "
            f"sizes={sizes}, min={BATCH_MIN_RECORDS}, max={max_shard_size}"
        )
    return sizes
