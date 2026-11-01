"""Delivers a just-committed turn's outbox rows to memory, best effort.

Runs after state_writer's commit and before the SSE done event. It never
raises and never alters the turn: whatever it cannot deliver within the cap
stays in memory_outbox and is picked up by the sweep.
"""

import uuid

from app.services import memory_relay_service


async def deliver_after_commit(playthrough_id: uuid.UUID) -> None:
    """Try to deliver this playthrough's pending rows within the delivery cap."""
    await memory_relay_service.deliver_best_effort(playthrough_id)
