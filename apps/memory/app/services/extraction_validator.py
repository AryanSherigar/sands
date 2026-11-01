"""Code validation of extraction output. Pure, no I/O: the model never decides identity."""

import re
from collections import Counter
from dataclasses import dataclass, field

from app.models.extraction import (
    CommitmentUpdate,
    ExtractedFact,
    ExtractionOutput,
    NewCommitment,
    NewEntity,
    SceneClaim,
    SupersessionClaim,
    ValidatedPlan,
)
from app.repositories.entity_repo import normalize_alias

NON_PREDICATE_CHARACTERS = re.compile(r"[^a-z0-9]+")
DROP_UNKNOWN_ID = "unknown_id"
DROP_BAD_EVIDENCE = "bad_evidence"
DROP_REJECTED_MUTATION = "rejected_mutation"
DROP_TRACKED_FIELD = "tracked_field"
DROP_EMPTY_FIELD = "empty_field"
DROP_NOT_SUPERSEDABLE = "not_supersedable"
DROP_DUPLICATE = "duplicate"
DROP_TEMPLATE_SCOPE_ITEM = "template_scope_item"
DROP_NEGATED_PREDICATE = "negated_predicate"
NEGATION_PREDICATE_TOKENS = frozenset(
    {
        "not",
        "never",
        "cannot",
        "cant",
        "wont",
        "didnt",
        "doesnt",
        "hasnt",
        "isnt",
        "without",
    }
)
NOTE_AUTHORED_COLLISION = "authored_name_collision"
NOTE_UNKNOWN_COUNTERPARTY = "unknown_counterparty"


@dataclass(frozen=True)
class RejectedTarget:
    entity_id: str
    predicate: str


@dataclass(frozen=True)
class ValidationContext:
    batch_labels: frozenset[str]
    roster_entity_ids: frozenset[str]
    supersedable_fact_ids: frozenset[str]
    open_commitment_ids: frozenset[str]
    tracked_predicates: frozenset[str]
    rejected_targets: frozenset[RejectedTarget]
    extracted_aliases: dict[str, list[str]] = field(default_factory=dict)
    authored_aliases: frozenset[str] = frozenset()
    is_template_scope: bool = False
    is_negated_predicate_rejected: bool = False


def normalize_predicate(predicate: str) -> str:
    return NON_PREDICATE_CHARACTERS.sub("_", predicate.strip().lower()).strip("_")


def _clean_evidence(evidence: list[str], ctx: ValidationContext) -> list[str]:
    return [label for label in dict.fromkeys(evidence) if label in ctx.batch_labels]


@dataclass
class _Resolution:
    valid_refs: set[str]
    kept_entities: list[NewEntity]
    reused: dict[str, str]
    drops: Counter[str]


def _matching_extracted_ids(entity: NewEntity, ctx: ValidationContext) -> set[str]:
    names = [entity.name, *entity.aliases]
    matches: set[str] = set()
    for name in names:
        matches.update(ctx.extracted_aliases.get(normalize_alias(name), []))
    return matches


def _collides_with_authored(entity: NewEntity, ctx: ValidationContext) -> bool:
    names = [normalize_alias(name) for name in [entity.name, *entity.aliases]]
    return any(name in ctx.authored_aliases for name in names)


def _resolve_entity(
    entity: NewEntity, ctx: ValidationContext, state: _Resolution
) -> None:
    evidence = _clean_evidence(entity.evidence, ctx)
    if not entity.temp_key or not entity.name.strip() or not evidence:
        state.drops[DROP_BAD_EVIDENCE if entity.name.strip() else DROP_EMPTY_FIELD] += 1
        return
    if entity.temp_key in state.valid_refs:
        state.drops[DROP_DUPLICATE] += 1
        return
    state.valid_refs.add(entity.temp_key)
    if _collides_with_authored(entity, ctx):
        state.drops[NOTE_AUTHORED_COLLISION] += 1
    matches = _matching_extracted_ids(entity, ctx)
    if len(matches) == 1 and not _collides_with_authored(entity, ctx):
        state.reused[entity.temp_key] = next(iter(matches))
        return
    state.kept_entities.append(entity.model_copy(update={"evidence": evidence}))


def _resolve_entities(output: ExtractionOutput, ctx: ValidationContext) -> _Resolution:
    state = _Resolution(set(ctx.roster_entity_ids), [], {}, Counter())
    for entity in output.new_entities:
        _resolve_entity(entity, ctx, state)
    return state


def _is_rejected(fact: ExtractedFact, predicate: str, ctx: ValidationContext) -> bool:
    if fact.assertion != "occurred":
        return False
    return RejectedTarget(fact.subject, predicate) in ctx.rejected_targets


def _is_negated_predicate(fact: ExtractedFact, predicate: str) -> bool:
    if fact.assertion != "occurred":
        return False
    return bool(NEGATION_PREDICATE_TOKENS & set(predicate.split("_")))


def _fact_problem(
    fact: ExtractedFact, predicate: str, refs: set[str], ctx: ValidationContext
) -> str | None:
    referenced = [fact.subject, fact.object, fact.speaker]
    if any(ref is not None and ref not in refs for ref in referenced):
        return DROP_UNKNOWN_ID
    has_object = bool(fact.object) or bool((fact.object_literal or "").strip())
    if not predicate or not has_object:
        return DROP_EMPTY_FIELD
    if predicate in ctx.tracked_predicates:
        return DROP_TRACKED_FIELD
    if _is_rejected(fact, predicate, ctx):
        return DROP_REJECTED_MUTATION
    if ctx.is_negated_predicate_rejected and _is_negated_predicate(fact, predicate):
        return DROP_NEGATED_PREDICATE
    return None


def _fact_key(
    fact: ExtractedFact, predicate: str
) -> tuple[str, str, str | None, str | None, str]:
    return (fact.subject, predicate, fact.object, fact.object_literal, fact.assertion)


def _fact_verdict(
    fact: ExtractedFact,
    predicate: str,
    refs: set[str],
    ctx: ValidationContext,
    seen: set[tuple[str, str, str | None, str | None, str]],
) -> str | None:
    problem = _fact_problem(fact, predicate, refs, ctx)
    if problem is None and not _clean_evidence(fact.evidence, ctx):
        return DROP_BAD_EVIDENCE
    if problem is None and _fact_key(fact, predicate) in seen:
        return DROP_DUPLICATE
    return problem


def _validate_facts(
    output: ExtractionOutput,
    refs: set[str],
    ctx: ValidationContext,
    drops: Counter[str],
) -> list[ExtractedFact]:
    kept: list[ExtractedFact] = []
    seen: set[tuple[str, str, str | None, str | None, str]] = set()
    for fact in output.facts:
        predicate = normalize_predicate(fact.predicate)
        problem = _fact_verdict(fact, predicate, refs, ctx, seen)
        if problem is not None:
            drops[problem] += 1
            continue
        seen.add(_fact_key(fact, predicate))
        evidence = _clean_evidence(fact.evidence, ctx)
        kept.append(
            fact.model_copy(update={"predicate": predicate, "evidence": evidence})
        )
    return kept


def _validate_supersessions(
    output: ExtractionOutput, ctx: ValidationContext, drops: Counter[str]
) -> list[SupersessionClaim]:
    kept: list[SupersessionClaim] = []
    for claim in output.supersessions:
        evidence = _clean_evidence(claim.evidence, ctx)
        if claim.fact_id not in ctx.supersedable_fact_ids:
            drops[DROP_NOT_SUPERSEDABLE] += 1
        elif not evidence:
            drops[DROP_BAD_EVIDENCE] += 1
        else:
            kept.append(claim.model_copy(update={"evidence": evidence}))
    return kept


def _validate_commitment(
    commitment: NewCommitment,
    refs: set[str],
    ctx: ValidationContext,
    drops: Counter[str],
) -> NewCommitment | None:
    evidence = _clean_evidence(commitment.evidence, ctx)
    if commitment.owner not in refs:
        drops[DROP_UNKNOWN_ID] += 1
    elif not evidence:
        drops[DROP_BAD_EVIDENCE] += 1
    elif not commitment.summary.strip():
        drops[DROP_EMPTY_FIELD] += 1
    else:
        counterparty = commitment.counterparty
        if counterparty is not None and counterparty not in refs:
            drops[NOTE_UNKNOWN_COUNTERPARTY] += 1
            counterparty = None
        return commitment.model_copy(
            update={"evidence": evidence, "counterparty": counterparty}
        )
    return None


def _validate_commitments(
    output: ExtractionOutput,
    refs: set[str],
    ctx: ValidationContext,
    drops: Counter[str],
) -> list[NewCommitment]:
    validated = (
        _validate_commitment(item, refs, ctx, drops) for item in output.new_commitments
    )
    return [item for item in validated if item is not None]


def _validate_updates(
    output: ExtractionOutput, ctx: ValidationContext, drops: Counter[str]
) -> list[CommitmentUpdate]:
    kept: list[CommitmentUpdate] = []
    for update in output.commitment_updates:
        evidence = _clean_evidence(update.evidence, ctx)
        if update.commitment_id not in ctx.open_commitment_ids:
            drops[DROP_UNKNOWN_ID] += 1
        elif not evidence:
            drops[DROP_BAD_EVIDENCE] += 1
        else:
            kept.append(update.model_copy(update={"evidence": evidence}))
    return kept


def _validate_scene(
    output: ExtractionOutput,
    refs: set[str],
    ctx: ValidationContext,
    drops: Counter[str],
) -> SceneClaim | None:
    scene = output.scene
    if scene is None:
        return None
    evidence = _clean_evidence(scene.evidence, ctx)
    location = scene.location if scene.location in refs else None
    present = [ref for ref in dict.fromkeys(scene.present) if ref in refs]
    if not evidence or (location is None and not present):
        drops[DROP_BAD_EVIDENCE if not evidence else DROP_UNKNOWN_ID] += 1
        return None
    return SceneClaim(location=location, present=present, evidence=evidence)


def _count_template_scope_items(output: ExtractionOutput, drops: Counter[str]) -> None:
    ignored = (
        len(output.supersessions)
        + len(output.new_commitments)
        + len(output.commitment_updates)
        + (1 if output.scene is not None else 0)
    )
    if ignored:
        drops[DROP_TEMPLATE_SCOPE_ITEM] += ignored


def validate_output(output: ExtractionOutput, ctx: ValidationContext) -> ValidatedPlan:
    resolution = _resolve_entities(output, ctx)
    drops = resolution.drops
    refs = resolution.valid_refs
    facts = _validate_facts(output, refs, ctx, drops)
    if ctx.is_template_scope:
        _count_template_scope_items(output, drops)
        return ValidatedPlan(
            new_entities=resolution.kept_entities,
            reused_entities=resolution.reused,
            facts=facts,
            dropped=dict(drops),
        )
    return ValidatedPlan(
        new_entities=resolution.kept_entities,
        reused_entities=resolution.reused,
        facts=facts,
        supersessions=_validate_supersessions(output, ctx, drops),
        new_commitments=_validate_commitments(output, refs, ctx, drops),
        commitment_updates=_validate_updates(output, ctx, drops),
        scene=_validate_scene(output, refs, ctx, drops),
        dropped=dict(drops),
    )
