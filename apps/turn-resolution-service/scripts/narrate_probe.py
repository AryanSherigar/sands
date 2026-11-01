"""Narrates one probe with the real prompt assembly and the real narrator client.

Dev tooling for the memory evaluation's generation layer: reads one JSON request on
stdin, builds the prompt through `context_assembly.assemble_prompt` exactly as a turn
would, and either prints it (`is_dry_run`) or streams `sample_count` narrations from
the configured narrator. Writes one JSON result on stdout. The memory evaluation runs
this as a subprocess so it never imports TRS.

Run from apps/turn-resolution-service with its own venv:
    .venv/bin/python scripts/narrate_probe.py < request.json
"""

import asyncio
import sys
import uuid

from app.config import settings
from app.integrations import narration_router
from app.models.memory import MemoryContext
from app.models.token_usage import TokenUsage
from app.models.turn import LoadedState, RecentTurn, TurnContext, TurnRequest
from app.turn import context_assembly
from app.turn.steps.ai_orchestrator import _build_system_instruction
from pydantic import BaseModel, Field


class NarrateRequest(BaseModel):
    scenario_id: uuid.UUID
    scenario_snapshot: dict[str, object]
    state: dict[str, object] = Field(default_factory=dict)
    turn_count: int
    playthrough_id: uuid.UUID
    participant_id: uuid.UUID
    action_text: str
    action_mode: str = "do"
    recent_turns: list[RecentTurn] = Field(default_factory=list)
    participant_names: dict[uuid.UUID, str] = Field(default_factory=dict)
    memory: MemoryContext = Field(default_factory=MemoryContext)
    sample_count: int = Field(default=1, ge=1)
    is_dry_run: bool = False


class NarrateResult(BaseModel):
    system_instruction: str
    prompt: str
    estimated_prompt_tokens: int
    narrations: list[str] = Field(default_factory=list)
    prompt_tokens: list[int] = Field(default_factory=list)
    completion_tokens: list[int] = Field(default_factory=list)


def build_prompt_parts(request: NarrateRequest) -> tuple[str, str]:
    turn_request = TurnRequest(
        playthrough_id=request.playthrough_id,
        participant_id=request.participant_id,
        client_action_id=uuid.uuid4(),
        action_text=request.action_text,
        action_mode=request.action_mode,
        turn_count=request.turn_count,
    )
    loaded_state = LoadedState(
        scenario_id=request.scenario_id,
        scenario_snapshot=request.scenario_snapshot,
        state=request.state,
        turn_count=request.turn_count,
        checkpoint=None,
    )
    context = TurnContext(
        memory=request.memory,
        recent_turns=request.recent_turns,
        participant_names=request.participant_names,
    )
    prompt = context_assembly.assemble_prompt(turn_request, loaded_state, context)
    return _build_system_instruction(loaded_state), prompt


async def narrate_once(system_instruction: str, prompt: str) -> tuple[str, TokenUsage]:
    usage = TokenUsage()
    chunks = [
        chunk
        async for chunk in narration_router.stream_narration(
            system_instruction, prompt, settings.narration_timeout_seconds, usage
        )
    ]
    return "".join(chunks), usage


async def run(request: NarrateRequest) -> NarrateResult:
    system_instruction, prompt = build_prompt_parts(request)
    result = NarrateResult(
        system_instruction=system_instruction,
        prompt=prompt,
        estimated_prompt_tokens=context_assembly.estimate_tokens(prompt),
    )
    if request.is_dry_run:
        return result
    for _ in range(request.sample_count):
        text, usage = await narrate_once(system_instruction, prompt)
        result.narrations.append(text)
        result.prompt_tokens.append(usage.prompt_tokens or 0)
        result.completion_tokens.append(usage.completion_tokens or 0)
    return result


def main() -> None:
    request = NarrateRequest.model_validate_json(sys.stdin.read())
    result = asyncio.run(run(request))
    sys.stdout.write(result.model_dump_json())


if __name__ == "__main__":
    main()
