"""Turns corpus keys into the real wire models: template build, ingest items, retrieve request."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.models.ingest import (
    AcceptedDelta,
    AcceptedDeltaItem,
    FlushItem,
    IngestItem,
    ParticipantsItem,
    ParticipantsPayload,
    PlayerEntityPayload,
    RegisterItem,
    RegisterPayload,
    RejectedCall,
    TurnItem,
    TurnPayload,
)
from app.models.retrieve import MAX_LAST_UTTERANCE_CHARS, RetrieveRequest
from app.models.templates import (
    MasterTemplateContent,
    NewbieTemplateContent,
    ParticipantPayload,
    StoryCardPayload,
    TemplateBuildRequest,
    TemplateEntityPayload,
    TemplateFactPayload,
)

from eval.corpus_loader import Campaign
from eval.corpus_models import DeltaDef, ProbeDef, TurnDef
from eval.keys import (
    PLAYTHROUGH_KEY,
    SCENARIO_KEY,
    key_uuid,
    turn_uuid,
)

PUBLISH_REVISION = 1
CORPUS_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
RECENT_TEXT_TURNS = 6


def scenario_id_of(campaign: Campaign) -> UUID:
    return key_uuid(campaign.campaign_id, SCENARIO_KEY)


def participant_uuid(campaign: Campaign, playthrough_key: str, key: str) -> UUID:
    return key_uuid(campaign.campaign_id, f"{playthrough_key}:participant:{key}")


def _entity_payload(campaign: Campaign) -> list[TemplateEntityPayload]:
    return [
        TemplateEntityPayload(
            entity_id=key_uuid(campaign.campaign_id, entity.key),
            entity_type=entity.entity_type,
            canonical_name=entity.canonical_name,
            aliases=entity.aliases,
            description=entity.description,
            is_player=entity.is_player,
        )
        for entity in campaign.scenario.entities
    ]


def _optional_uuid(campaign: Campaign, key: str | None) -> UUID | None:
    return key_uuid(campaign.campaign_id, key) if key else None


def _fact_payload(campaign: Campaign) -> list[TemplateFactPayload]:
    return [
        TemplateFactPayload(
            fact_id=key_uuid(campaign.campaign_id, fact.key),
            subject_entity_id=key_uuid(campaign.campaign_id, fact.subject_key),
            predicate=fact.predicate,
            object_entity_id=_optional_uuid(campaign, fact.object_key),
            object_literal=fact.object_literal,
            when_active=fact.when_active,
            hidden=fact.is_hidden,
            superseded_fact_id=_optional_uuid(campaign, fact.superseded_fact_key),
        )
        for fact in campaign.scenario.facts
    ]


def _newbie_content(campaign: Campaign) -> NewbieTemplateContent:
    scenario = campaign.scenario
    return NewbieTemplateContent(
        story_cards=[
            StoryCardPayload(
                card_id=card.card_id,
                type=card.type,
                name=card.name,
                content=card.content,
            )
            for card in scenario.cards
        ],
        world_lore=scenario.world_lore,
        single_lore_prompt=scenario.single_lore_prompt,
        main_conflict=scenario.main_conflict,
        opening_prompt=scenario.opening_prompt,
    )


def build_template_request(campaign: Campaign) -> TemplateBuildRequest:
    is_master = campaign.scenario.mode == "master"
    return TemplateBuildRequest(
        scenario_id=scenario_id_of(campaign),
        publish_revision=PUBLISH_REVISION,
        mode=campaign.scenario.mode,
        content_hash=campaign.content_hash,
        master=(
            MasterTemplateContent(
                entities=_entity_payload(campaign), facts=_fact_payload(campaign)
            )
            if is_master
            else None
        ),
        newbie=None if is_master else _newbie_content(campaign),
    )


def playthrough_id_of(
    campaign: Campaign, playthrough_key: str = PLAYTHROUGH_KEY
) -> UUID:
    return key_uuid(campaign.campaign_id, playthrough_key)


def _participants(campaign: Campaign, playthrough_key: str) -> list[ParticipantPayload]:
    return [
        ParticipantPayload(
            participant_id=participant_uuid(campaign, playthrough_key, item.key),
            display_name=item.display_name,
        )
        for item in campaign.scenario.participants
    ]


PLAYER_FALLBACK_KEY = "player"
NEWBIE_PLAYER_TYPE = "character"


def registered_player_key(campaign: Campaign) -> str | None:
    """The entity registered as the player, mirroring Core: authored in master mode, and
    for newbie one entity named after the owner (matched to the scenario's entity list)."""
    scenario = campaign.scenario
    if scenario.player_entity_key or scenario.mode != "newbie":
        return scenario.player_entity_key
    owner = scenario.participants[0].display_name
    matched = next(
        (e.key for e in scenario.entities if e.canonical_name == owner), None
    )
    return matched or PLAYER_FALLBACK_KEY


def _player_payload(campaign: Campaign) -> PlayerEntityPayload | None:
    key = registered_player_key(campaign)
    entity = next((e for e in campaign.scenario.entities if e.key == key), None)
    if entity is not None:
        return PlayerEntityPayload(
            authored_entity_id=key_uuid(campaign.campaign_id, entity.key),
            canonical_name=entity.canonical_name,
            aliases=entity.aliases,
            entity_type=entity.entity_type,
        )
    if key != PLAYER_FALLBACK_KEY:
        return None
    return PlayerEntityPayload(
        authored_entity_id=key_uuid(campaign.campaign_id, PLAYER_FALLBACK_KEY),
        canonical_name=campaign.scenario.participants[0].display_name,
        entity_type=NEWBIE_PLAYER_TYPE,
    )


def build_register_items(campaign: Campaign, playthrough_key: str) -> list[IngestItem]:
    register = RegisterItem(
        item_kind="register_playthrough",
        sequence=0,
        payload=RegisterPayload(
            scenario_id=scenario_id_of(campaign),
            publish_revision=PUBLISH_REVISION,
            player_entity=_player_payload(campaign),
            participants=_participants(campaign, playthrough_key),
            tracked_fields=campaign.scenario.tracked_fields,
        ),
    )
    return [register]


def _delta_item(campaign: Campaign, delta: DeltaDef) -> AcceptedDeltaItem:
    entity_id = key_uuid(campaign.campaign_id, delta.entity_key)
    return AcceptedDeltaItem(
        kind=delta.kind,
        key=f"{entity_id}.{delta.attribute}",
        before=delta.before,
        after=delta.after,
    )


def _turn_item(campaign: Campaign, turn: TurnDef, playthrough_key: str) -> TurnItem:
    payload = TurnPayload(
        turn_id=turn_uuid(campaign.campaign_id, playthrough_key, turn.turn_number),
        turn_number=turn.turn_number,
        participant_id=participant_uuid(
            campaign, playthrough_key, turn.participant_key
        ),
        action_mode=turn.action_mode,
        action_text=turn.action_text,
        narration_text=turn.narration_text,
        accepted_delta=AcceptedDelta(
            items=[_delta_item(campaign, delta) for delta in turn.delta]
        ),
        rejected_calls=[
            RejectedCall(**call.model_dump()) for call in turn.rejected_calls
        ],
        created_at=CORPUS_EPOCH + timedelta(minutes=turn.turn_number),
    )
    return TurnItem(item_kind="turn", sequence=turn.turn_number, payload=payload)


def build_turn_items(
    campaign: Campaign, turns: list[TurnDef], playthrough_key: str
) -> list[IngestItem]:
    return [_turn_item(campaign, turn, playthrough_key) for turn in turns]


def build_flush_item(sequence: int) -> IngestItem:
    return FlushItem(item_kind="flush", sequence=sequence)


def build_participants_item(campaign: Campaign, playthrough_key: str) -> IngestItem:
    return ParticipantsItem(
        item_kind="participants",
        sequence=0,
        payload=ParticipantsPayload(
            participants=_participants(campaign, playthrough_key)
        ),
    )


def render_recent_text(turns: list[TurnDef], at_turn: int) -> str:
    window = [
        t for t in turns if at_turn - RECENT_TEXT_TURNS < t.turn_number <= at_turn
    ]
    return "\n\n".join(f"{t.action_text}\n{t.narration_text}" for t in window)


def last_say_utterance(turns: list[TurnDef], at_turn: int) -> str:
    """Mirrors TRS: the action text of the latest say-mode turn in the recent window."""
    window = [
        t for t in turns if at_turn - RECENT_TEXT_TURNS < t.turn_number <= at_turn
    ]
    for turn in reversed(window):
        if turn.action_mode == "say":
            return turn.action_text.strip()[:MAX_LAST_UTTERANCE_CHARS]
    return ""


def _uuids(campaign: Campaign, keys: list[str]) -> list[UUID]:
    return [key_uuid(campaign.campaign_id, key) for key in keys]


def _participant_names(campaign: Campaign) -> dict[UUID, str]:
    return {
        participant_uuid(campaign, PLAYTHROUGH_KEY, item.key): item.display_name
        for item in campaign.scenario.participants
    }


def build_retrieve_request(
    campaign: Campaign,
    probe: ProbeDef,
    recall_budget_tokens: int | None = None,
    recent_window_turns: int | None = None,
) -> RetrieveRequest:
    snapshot = campaign.turns[probe.at_turn - 1].snapshot
    return RetrieveRequest(
        playthrough_id=playthrough_id_of(campaign),
        sequence=probe.at_turn,
        action_text=probe.action_text,
        action_mode=probe.action_mode,
        actor_participant_id=participant_uuid(
            campaign, PLAYTHROUGH_KEY, probe.actor_key
        ),
        recent_text=render_recent_text(campaign.turns, probe.at_turn),
        last_actor_utterance=last_say_utterance(campaign.turns, probe.at_turn),
        scene_authored_entity_ids=_uuids(campaign, snapshot.scene_entity_keys),
        interlocutor_authored_entity_id=_optional_uuid(
            campaign, snapshot.interlocutor_key
        ),
        revealed_fact_ids=_uuids(campaign, snapshot.revealed_fact_keys),
        active_conditional_fact_ids=_uuids(
            campaign, snapshot.active_conditional_fact_keys
        ),
        participant_names=_participant_names(campaign),
        recent_window_turns=recent_window_turns,
        recall_budget_tokens=recall_budget_tokens,
    )
