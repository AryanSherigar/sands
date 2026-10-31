"""Per-tool authored-row counters, registered by each tool's own module."""

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

DataCounter = Callable[[AsyncSession, uuid.UUID], Awaitable[int]]

_COUNTERS: dict[str, DataCounter] = {}


def register_data_counter(tool_key: str, counter: DataCounter) -> None:
    _COUNTERS[tool_key] = counter


async def count_tool_rows(
    session: AsyncSession, tool_key: str, scenario_id: uuid.UUID
) -> int:
    counter = _COUNTERS.get(tool_key)
    if counter is None:
        return 0
    return await counter(session, scenario_id)
