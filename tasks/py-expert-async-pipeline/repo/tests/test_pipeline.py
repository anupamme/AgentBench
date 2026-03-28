import asyncio

import pytest
from pipeline import AsyncPipeline


@pytest.mark.asyncio
async def test_async_pipeline_basic():
    async def double(x):
        await asyncio.sleep(0)
        return x * 2

    async def add_one(x):
        await asyncio.sleep(0)
        return x + 1

    p = AsyncPipeline([double, add_one])
    results = await p.run([1, 2, 3])
    assert sorted(results) == [3, 5, 7]


@pytest.mark.asyncio
async def test_async_pipeline_empty_stages():
    p = AsyncPipeline([])
    results = await p.run([1, 2, 3])
    assert results == [1, 2, 3]


@pytest.mark.asyncio
async def test_async_pipeline_concurrent():
    started = []

    async def slow_stage(x):
        started.append(x)
        await asyncio.sleep(0.01)
        return x

    p = AsyncPipeline([slow_stage])
    await p.run([1, 2, 3])
    assert len(started) == 3
