import json

import structlog
from pydantic import TypeAdapter, ValidationError
from strategy_contracts.limits import MAX_CITED_GRUDGES, MAX_TERMS_PER_CARD
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.terms import Term

logger = structlog.get_logger()

EVENT_SCENE_DECISION_UNPARSEABLE = "scene_decision_unparseable"
EVENT_SCENE_TERM_DROPPED = "scene_term_dropped"
CITED_KEY = "cited_grudge_ids"
TERMS_KEY = "terms"
TIER_KEY = "peace_tier"
PROMISE_BY_RULER_KEY = "is_promise_by_ruler"
_TERM_ADAPTER: TypeAdapter[Term] = TypeAdapter(Term)
_VALID_TIERS = {tier.value for tier in PeaceTier}
_DECODER = json.JSONDecoder()


def _first_json_object(model_text: str) -> dict[str, object]:
    """The first balanced JSON object in the text, ignoring prose and code fences."""
    start = model_text.find("{")
    while start != -1:
        try:
            value, _ = _DECODER.raw_decode(model_text, start)
        except ValueError:
            start = model_text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = model_text.find("{", start + 1)
    raise ValueError("no JSON object")


def _is_valid_term(raw_term: object) -> bool:
    try:
        _TERM_ADAPTER.validate_python(raw_term)
    except ValidationError:
        logger.warning(EVENT_SCENE_TERM_DROPPED)
        return False
    return True


def _repair(raw: dict[str, object]) -> dict[str, object]:
    """Trim or drop the parts a model commonly gets wrong so the action survives."""
    cited = raw.get(CITED_KEY)
    if isinstance(cited, list):
        raw[CITED_KEY] = cited[:MAX_CITED_GRUDGES]
    terms = raw.get(TERMS_KEY)
    if isinstance(terms, list):
        raw[TERMS_KEY] = [term for term in terms if _is_valid_term(term)][
            :MAX_TERMS_PER_CARD
        ]
    if raw.get(PROMISE_BY_RULER_KEY) is None:
        raw.pop(PROMISE_BY_RULER_KEY, None)
    if raw.get(TIER_KEY) not in _VALID_TIERS:
        raw[TIER_KEY] = None
    return raw


def parse_decision(model_text: str) -> SceneDecision:
    """Read the narrator's JSON answer; anything unusable means keep talking."""
    try:
        return SceneDecision.model_validate(_repair(_first_json_object(model_text)))
    except (ValueError, ValidationError):
        logger.warning(EVENT_SCENE_DECISION_UNPARSEABLE)
        return SceneDecision(action=SceneAction.CONTINUE_TALK)
