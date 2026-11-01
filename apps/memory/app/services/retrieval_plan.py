"""Turns a request plus the registered playthrough into the inputs of one retrieval."""

from dataclasses import dataclass

from app.config import Settings
from app.models.eligibility import EligibilityContext
from app.models.retrieve import RetrieveRequest
from app.models.templates import PlaythroughRow
from app.services.eligibility import build_eligibility_context
from app.services.retrieval_types import Scope, build_scopes


@dataclass(frozen=True)
class RetrievalPlan:
    ctx: EligibilityContext
    recent_window_turns: int
    budget_tokens: int
    query_text: str
    scopes: list[Scope]


def build_query_text(request: RetrieveRequest) -> str:
    return f"{request.action_text} {request.last_actor_utterance}".strip()


def build_plan(
    request: RetrieveRequest, playthrough: PlaythroughRow, settings: Settings
) -> RetrievalPlan:
    """The scope comes from the registered playthrough row, never from the request."""
    window = request.recent_window_turns
    if window is None:
        window = settings.recent_window_turns
    budget = request.recall_budget_tokens
    if budget is None:
        budget = settings.recall_budget_tokens
    ctx = build_eligibility_context(
        playthrough_id=playthrough.playthrough_id,
        template_id=playthrough.template_id,
        at_seq=request.sequence,
        recent_window_turns=window,
        revealed_fact_ids=request.revealed_fact_ids,
        active_conditional_fact_ids=request.active_conditional_fact_ids,
    )
    return RetrievalPlan(
        ctx=ctx,
        recent_window_turns=window,
        budget_tokens=budget,
        query_text=build_query_text(request),
        scopes=build_scopes(playthrough.playthrough_id, playthrough.template_id),
    )
