"""Integration tests for rate-limit counters via PostgresRateLimitStore."""

import asyncio

from app.services.rate_limit.store import CounterLimit, PostgresRateLimitStore

DAY = 86400


async def test_reserve_takes_units_until_limit(
    rate_limit_store: PostgresRateLimitStore,
) -> None:
    results = [
        await rate_limit_store.reserve([CounterLimit("k:limit", 2)], DAY)
        for _ in range(3)
    ]

    assert [result.is_reserved for result in results] == [True, True, False]
    assert results[2].exceeded_key == "k:limit"


async def test_zero_limit_never_reserves(
    rate_limit_store: PostgresRateLimitStore,
) -> None:
    result = await rate_limit_store.reserve([CounterLimit("k:zero", 0)], DAY)

    assert not result.is_reserved


async def test_concurrent_reserves_never_overshoot(
    rate_limit_store: PostgresRateLimitStore,
) -> None:
    results = await asyncio.gather(
        *(rate_limit_store.reserve([CounterLimit("k:race", 5)], DAY) for _ in range(20))
    )

    assert sum(result.is_reserved for result in results) == 5
    assert await rate_limit_store.current_count("k:race", DAY) == 5


async def test_multi_counter_reserve_is_all_or_nothing(
    rate_limit_store: PostgresRateLimitStore,
) -> None:
    await rate_limit_store.reserve([CounterLimit("k:global", 1)], DAY)

    result = await rate_limit_store.reserve(
        [CounterLimit("k:user", 10), CounterLimit("k:global", 1)], DAY
    )

    assert result.exceeded_key == "k:global"
    assert await rate_limit_store.current_count("k:user", DAY) == 0


async def test_refund_returns_unit_and_floors_at_zero(
    rate_limit_store: PostgresRateLimitStore,
) -> None:
    reserved = await rate_limit_store.reserve([CounterLimit("k:refund", 1)], DAY)
    assert reserved.window_start is not None

    await rate_limit_store.refund(["k:refund"], reserved.window_start)
    await rate_limit_store.refund(["k:refund"], reserved.window_start)

    assert await rate_limit_store.current_count("k:refund", DAY) == 0


async def test_hit_sliding_window_counts_every_hit(
    rate_limit_store: PostgresRateLimitStore,
) -> None:
    for _ in range(3):
        hit = await rate_limit_store.hit_sliding_window("k:burst", 60)

    assert hit.current_count == 3
    assert hit.previous_count == 0
    assert 0 <= hit.elapsed_seconds < 60


async def test_delete_expired_keeps_live_rows(
    rate_limit_store: PostgresRateLimitStore,
) -> None:
    await rate_limit_store.reserve([CounterLimit("k:live", 5)], DAY)

    deleted = await rate_limit_store.delete_expired(lock_id=1)

    assert deleted == 0
    assert await rate_limit_store.current_count("k:live", DAY) == 1
