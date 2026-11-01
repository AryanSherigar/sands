"""Runs one campaign end to end: template, decoy, interleaved ingest and probes, extraction scoring."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID

from app.models.retrieve import RetrieveResponse
from psycopg import AsyncConnection

from eval.arms import score_both_arms
from eval.baseline_text import build_inline_text
from eval.corpus_loader import Campaign
from eval.corpus_models import PlantDef, ProbeDef
from eval.driver import (
    UsageTotals,
    drain,
    flush_playthrough,
    ingest_turns,
    register_playthrough,
)
from eval.errors import HarnessError, ModelMismatchError
from eval.extraction_observe import load_observation
from eval.keys import DECOY_PLAYTHROUGH_KEY, PLAYTHROUGH_KEY
from eval.labels import generate_labels
from eval.memory_http import MemoryHttp
from eval.payloads import (
    build_retrieve_request,
    build_template_request,
    playthrough_id_of,
    registered_player_key,
)
from eval.run_models import ExtractionRecord, IntervalOut, ProbeRecord, TypeScoreOut
from eval.scoring.extraction import (
    ExtractionObservation,
    ExtractionScore,
    TypeScore,
    score_extraction,
)
from eval.scoring.stats import Interval

MILLISECONDS_PER_SECOND = 1000


@dataclass
class RunEnv:
    http: MemoryHttp
    database_url: str
    on_sweep: Callable[[UsageTotals], None]
    expected_embedding_model: str
    is_quality: bool
    usage: UsageTotals = field(default_factory=UsageTotals)
    query_characters: int = 0


@dataclass
class CampaignOutcome:
    probes: list[ProbeRecord]
    extraction: ExtractionRecord
    observation: ExtractionObservation


def _interval_out(interval: Interval | None) -> IntervalOut | None:
    if interval is None:
        return None
    return IntervalOut(
        mean=interval.mean, low=interval.low, high=interval.high, count=interval.count
    )


def _type_out(score: TypeScore) -> TypeScoreOut:
    return TypeScoreOut(
        recall=_interval_out(score.recall),
        precision=_interval_out(score.precision),
        recall_hits=score.recall_hits,
        label_count=score.label_count,
        predicted_count=score.predicted_count,
        wrong_status=score.wrong_status,
    )


def extraction_record_of(campaign_id: str, score: ExtractionScore) -> ExtractionRecord:
    return ExtractionRecord(
        campaign_id=campaign_id,
        by_type={name: _type_out(item) for name, item in score.by_type.items()},
        forbidden_extracted=score.forbidden_extracted,
        duplicate_entity_rate=score.duplicate_entity_rate,
        new_entity_count=score.new_entity_count,
        negated_fact_count=score.negated_fact_count,
    )


def check_response(env: RunEnv, probe: ProbeDef, response: RetrieveResponse) -> None:
    if response.embedding_model != env.expected_embedding_model:
        raise ModelMismatchError(
            f"{probe.probe_id}: embedding model {response.embedding_model} is not pinned"
        )
    if env.is_quality and response.skipped_branches:
        raise HarnessError(
            f"{probe.probe_id}: skipped branches {response.skipped_branches}"
        )
    if env.is_quality and "indexing_lag" in response.degraded_reasons:
        raise HarnessError(f"{probe.probe_id}: indexing lag after a full drain")


async def _run_probe(
    env: RunEnv, campaign: Campaign, plants: dict[str, PlantDef], probe: ProbeDef
) -> list[ProbeRecord]:
    request = build_retrieve_request(campaign, probe)
    started = time.perf_counter()
    response = await env.http.retrieve(request)
    elapsed_ms = (time.perf_counter() - started) * MILLISECONDS_PER_SECOND
    check_response(env, probe, response)
    env.query_characters += len(probe.action_text)
    inline = build_inline_text(campaign, probe)
    names = {entity.key: entity.canonical_name for entity in campaign.scenario.entities}
    return score_both_arms(probe, plants, inline, response, elapsed_ms, names)


def _probes_by_turn(campaign: Campaign) -> dict[int, list[ProbeDef]]:
    grouped: dict[int, list[ProbeDef]] = {}
    for probe in campaign.probes:
        grouped.setdefault(probe.at_turn, []).append(probe)
    return dict(sorted(grouped.items()))


async def _prepare_template(env: RunEnv, campaign: Campaign) -> UUID:
    template = await env.http.build_template(build_template_request(campaign))
    await drain(env.http, None, env.usage, env.on_sweep)
    if campaign.decoy_turns:
        await register_playthrough(env.http, campaign, DECOY_PLAYTHROUGH_KEY)
        await ingest_turns(
            env.http, campaign, DECOY_PLAYTHROUGH_KEY, campaign.decoy_turns
        )
        await flush_playthrough(
            env.http, campaign, DECOY_PLAYTHROUGH_KEY, len(campaign.decoy_turns)
        )
        decoy_id = playthrough_id_of(campaign, DECOY_PLAYTHROUGH_KEY)
        await drain(env.http, decoy_id, env.usage, env.on_sweep)
    return template.template_id


async def _observe(
    env: RunEnv, campaign: Campaign, template_id: UUID
) -> ExtractionObservation:
    playthrough_id = playthrough_id_of(campaign)
    async with await AsyncConnection.connect(env.database_url) as connection:
        return await load_observation(connection, campaign, playthrough_id, template_id)


def authored_entity_keys(campaign: Campaign) -> set[str]:
    """Master templates author every entity; a newbie playthrough registers only the player."""
    if campaign.scenario.mode == "master":
        return {entity.key for entity in campaign.scenario.entities}
    player = registered_player_key(campaign)
    return {player} if player else set()


def _score_extraction(
    campaign: Campaign, observation: ExtractionObservation
) -> ExtractionRecord:
    authored = authored_entity_keys(campaign)
    score = score_extraction(generate_labels(campaign), observation, authored)
    return extraction_record_of(campaign.campaign_id, score)


async def run_campaign(env: RunEnv, campaign: Campaign) -> CampaignOutcome:
    template_id = await _prepare_template(env, campaign)
    playthrough_id = playthrough_id_of(campaign)
    plants = {plant.plant_id: plant for plant in campaign.plants}
    await register_playthrough(env.http, campaign, PLAYTHROUGH_KEY)
    records: list[ProbeRecord] = []
    ingested = 0
    for at_turn, probes in _probes_by_turn(campaign).items():
        await ingest_turns(
            env.http, campaign, PLAYTHROUGH_KEY, campaign.turns[ingested:at_turn]
        )
        ingested = at_turn
        await drain(env.http, playthrough_id, env.usage, env.on_sweep)
        for probe in probes:
            records.extend(await _run_probe(env, campaign, plants, probe))
    await ingest_turns(env.http, campaign, PLAYTHROUGH_KEY, campaign.turns[ingested:])
    await flush_playthrough(env.http, campaign, PLAYTHROUGH_KEY, len(campaign.turns))
    await drain(env.http, playthrough_id, env.usage, env.on_sweep)
    observation = await _observe(env, campaign, template_id)
    return CampaignOutcome(
        records, _score_extraction(campaign, observation), observation
    )
