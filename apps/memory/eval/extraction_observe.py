"""Turns stored, validated extraction plans into scorable observations (read-only)."""

import re
from uuid import UUID

from app.models.extraction import ValidatedPlan
from app.models.facts import EntityRow
from app.repositories import entity_repo, extraction_batch_repo
from app.repositories.entity_repo import normalize_alias
from app.services.retrieval_types import build_scopes
from psycopg import AsyncConnection

from eval.corpus_loader import Campaign
from eval.keys import key_uuid
from eval.scoring.extraction import (
    ExtractionObservation,
    ObservedCommitment,
    ObservedEntity,
    ObservedFact,
)

EVIDENCE_PATTERN = re.compile(r"^S(\d+)\.\d+$")
APPLIED_STATUS = "applied"


def evidence_turns(evidence: list[str]) -> frozenset[int]:
    matches = (EVIDENCE_PATTERN.match(label) for label in evidence)
    return frozenset(int(match.group(1)) for match in matches if match)


def build_name_index(campaign: Campaign) -> dict[str, str]:
    index: dict[str, str] = {}
    for entity in campaign.scenario.entities:
        for name in [entity.canonical_name, *entity.aliases]:
            index[normalize_alias(name)] = entity.key
    return index


def _key_of_entity(
    row: EntityRow,
    authored: dict[UUID, str],
    names: dict[str, str],
    alias_texts: list[str],
) -> str | None:
    if row.authored_entity_id in authored:
        return authored[row.authored_entity_id]
    candidates = [normalize_alias(row.canonical_name), *alias_texts]
    return next((names[text] for text in candidates if text in names), None)


def build_entity_key_map(
    rows: list[EntityRow],
    aliases: list[tuple[str, UUID]],
    campaign: Campaign,
) -> dict[str, str | None]:
    authored = {
        key_uuid(campaign.campaign_id, entity.key): entity.key
        for entity in campaign.scenario.entities
    }
    names = build_name_index(campaign)
    alias_texts: dict[UUID, list[str]] = {}
    for alias, entity_id in aliases:
        alias_texts.setdefault(entity_id, []).append(alias)
    return {
        str(row.entity_id): _key_of_entity(
            row, authored, names, alias_texts.get(row.entity_id, [])
        )
        for row in rows
    }


class PlanResolver:
    def __init__(
        self,
        plan: ValidatedPlan,
        key_map: dict[str, str | None],
        names: dict[str, str],
        display_names: dict[str, str],
    ) -> None:
        self._plan = plan
        self._key_map = key_map
        self._names = names
        self._display_names = display_names
        self._temp_names = {
            entity.temp_key: entity.name for entity in plan.new_entities
        }

    def key_of(self, reference: str | None) -> str | None:
        if reference is None:
            return None
        if reference in self._plan.reused_entities:
            return self._key_map.get(self._plan.reused_entities[reference])
        if reference in self._temp_names:
            return self._names.get(normalize_alias(self._temp_names[reference]))
        return self._key_map.get(reference)

    def name_of(self, reference: str | None) -> str:
        if reference is None:
            return ""
        entity_id = self._plan.reused_entities.get(reference, reference)
        if (
            reference in self._temp_names
            and reference not in self._plan.reused_entities
        ):
            return self._temp_names[reference]
        return self._display_names.get(entity_id, "")


def _observe_facts(plan: ValidatedPlan, resolver: PlanResolver) -> list[ObservedFact]:
    return [
        ObservedFact(
            turns=evidence_turns(fact.evidence),
            subject_key=resolver.key_of(fact.subject),
            predicate=fact.predicate,
            object_key=resolver.key_of(fact.object),
            object_text=fact.object_literal or resolver.name_of(fact.object),
            assertion=fact.assertion,
        )
        for fact in plan.facts
    ]


def _observe_commitments(
    plan: ValidatedPlan, resolver: PlanResolver
) -> list[ObservedCommitment]:
    opened = [
        ObservedCommitment(
            evidence_turns(item.evidence),
            resolver.key_of(item.owner),
            item.kind,
            "open",
            False,
        )
        for item in plan.new_commitments
    ]
    updated = [
        ObservedCommitment(evidence_turns(item.evidence), None, None, item.status, True)
        for item in plan.commitment_updates
    ]
    return opened + updated


def _observe_mentions(
    plan: ValidatedPlan, resolver: PlanResolver
) -> list[tuple[frozenset[int], str]]:
    pairs = [(fact.evidence, fact.subject) for fact in plan.facts]
    pairs += [(fact.evidence, fact.object) for fact in plan.facts]
    pairs += [(item.evidence, item.owner) for item in plan.new_commitments]
    resolved = [
        (evidence_turns(evidence), resolver.key_of(ref)) for evidence, ref in pairs
    ]
    return [(turns, key) for turns, key in resolved if key is not None]


def _observe_entities(
    plan: ValidatedPlan, names: dict[str, str]
) -> list[ObservedEntity]:
    created = [e for e in plan.new_entities if e.temp_key not in plan.reused_entities]
    return [ObservedEntity(e.name, names.get(normalize_alias(e.name))) for e in created]


def observe_plans(
    plans: list[ValidatedPlan],
    key_map: dict[str, str | None],
    names: dict[str, str],
    display_names: dict[str, str] | None = None,
) -> ExtractionObservation:
    observation = ExtractionObservation()
    for plan in plans:
        resolver = PlanResolver(plan, key_map, names, display_names or {})
        observation.facts.extend(_observe_facts(plan, resolver))
        observation.commitments.extend(_observe_commitments(plan, resolver))
        observation.supersession_turns.extend(
            evidence_turns(s.evidence) for s in plan.supersessions
        )
        observation.mentions.extend(_observe_mentions(plan, resolver))
        observation.new_entities.extend(_observe_entities(plan, names))
    return observation


async def load_observation(
    connection: AsyncConnection,
    campaign: Campaign,
    playthrough_id: UUID,
    template_id: UUID,
) -> ExtractionObservation:
    batches = await extraction_batch_repo.list_batches(
        connection, "playthrough", playthrough_id, [APPLIED_STATUS]
    )
    plans = [
        ValidatedPlan.model_validate(b.validated_plan)
        for b in batches
        if b.validated_plan
    ]
    scopes = build_scopes(playthrough_id, template_id)
    rows = await entity_repo.get_entities(connection, scopes)
    aliases = await entity_repo.list_aliases_in_scopes(connection, scopes)
    key_map = build_entity_key_map(rows, aliases, campaign)
    display_names = {str(row.entity_id): row.canonical_name for row in rows}
    return observe_plans(plans, key_map, build_name_index(campaign), display_names)
