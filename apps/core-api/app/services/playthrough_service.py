"""Playthrough domain service: creation, snapshotting, and access-gated reads."""

import random
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field

import structlog
from app.config import settings
from app.db.models.fact import Fact
from app.db.models.map_pin import MapPin
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import PRIVATE_VISIBILITY, Scenario
from app.db.models.scenario_condition import ScenarioCondition
from app.db.models.scenario_music import MOOD_SLOTS
from app.db.models.turn_log import TurnLog
from app.exceptions.alpha_exceptions import (
    AlphaConsentRequiredError,
    AlphaFeatureDisabledError,
    AlphaScenarioOnlyError,
)
from app.exceptions.playthrough_exceptions import (
    InvalidSetupValuesError,
    InvalidShareTokenError,
    InvalidStateOverrideError,
    PlaythroughAccessDeniedError,
    PlaythroughNotFoundError,
    PlaythroughNotJoinableError,
    ScenarioNotPublishedError,
    SoloScenarioJoinError,
    StrategyFactionRequiredError,
)
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.integrations import simulation_client
from app.logging_config import log_audit_event
from app.models.memory_outbox import (
    ParticipantsPayload,
    RegisterParticipant,
    RegisterPayload,
    RegisterPlayerEntity,
    RegisterSetupFact,
)
from app.models.minigame import (
    COMPOSURE_TYPE,
    ComposureConfig,
    DodgeConfig,
    LockpickConfig,
)
from app.models.playthrough import (
    ParticipantSummary,
    PlaythroughCharacterUpdate,
    PlaythroughCreate,
    PlaythroughResponse,
    RuleSheetItem,
)
from app.models.turn_log import (
    ToolCallLogEntry,
    TurnLogListResponse,
    TurnLogResponse,
)
from app.repositories.condition_repo import ConditionRepo
from app.repositories.end_condition_repo import EndConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.invariant_repo import InvariantRepo
from app.repositories.map_repo import MapRepo
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.minigame_repo import MinigameRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import (
    ACTIVE_STATUS,
    INITIALIZING_STATUS,
    PlaythroughRepo,
)
from app.repositories.rule_check_repo import RuleCheckRepo
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.share_repo import ShareRepo
from app.repositories.sheet_rule_repo import SheetRuleRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.user_repo import UserRepo
from app.services import default_music, strategy_playthrough, tier_music
from app.services.alpha_consent import is_alpha_consent_current
from app.services.condition_state import list_active_condition_labels
from app.services.display_hints import STATUS_HUD_TOOL_KEY, strip_display_hints
from app.services.initial_state import materialise_initial_state
from app.services.narrator_rules import (
    SNAPSHOT_KEY_INTENT_MARKER_GROUP,
    SNAPSHOT_KEY_NARRATION_MAX_OUTPUT_TOKENS,
    intent_marker_group_from_rules,
    narration_limit_from_rules,
)
from app.services.opening_scene import render_opening_scene
from app.services.rule_sheet_state import RULE_STATUS_ROOT
from app.services.rule_sheet_view import rule_sheet_view
from app.services.scenario_access import ScenarioAccessChecker
from app.services.schema_field_validation import (
    RULE_CHECKS_TOOL_KEY,
    strip_initial_random,
)
from app.services.state_override_validation import (
    merge_state_overrides,
    validate_state_overrides,
)
from app.services.state_visibility import (
    client_snapshot,
    redact_hidden_tool_calls,
    visible_state,
)
from app.tools.registry import STATE_SCHEMA_EXTENSION_KEY, contribute_snapshot
from strategy_contracts.scenario import PlayerRulerCustomization, StrategyScenario

logger = structlog.get_logger()

EVENT_PLAYTHROUGH_STARTED = "playthrough_started"
NEWBIE_PLAYER_ENTITY_KEY = "newbie-player"
FALLBACK_PLAYER_NAME = "The Player"
NANOSECONDS_PER_MILLISECOND = 1_000_000
COMPOSURE_TOOL_KEY = "composure"
NEWBIE_PLAYER_ENTITY_TYPE = "character"
MASTER_MODE = "master"
REASON_PLAYTEST_ONLY = "only a playtest can preset values"

# NOTE: Mirrors app.models.scenario.RESERVED_STATE_SCHEMA_KEYS's two entries — kept
# as literal keys here (not a cross-package import) since this dict shape is
# TRS-facing snapshot content, not a Core-API request schema.
_CURRENT_LOCATION_FIELD = "current_location_id"
_DISCOVERED_LOCATIONS_FIELD = "discovered_location_ids"
_LOCATION_ENTITY_TYPE = "location"


def _render_fact_text(fact: Fact, name_by_entity_id: dict[str, str]) -> str:
    subject_name = name_by_entity_id.get(str(fact.subject_entity_id), "Something")
    object_text = (
        name_by_entity_id.get(str(fact.object_entity_id), "something")
        if fact.object_entity_id is not None
        else fact.object_literal
    )
    predicate = fact.predicate.replace("_", " ")
    return f"{subject_name} {predicate} {object_text}."


def _snapshot_fact(fact: Fact, name_by_entity_id: dict[str, str]) -> dict[str, object]:
    """TRS evaluates `when_active` against state to decide which conditional
    facts are eligible for recall; memory never sees the expression."""
    entry: dict[str, object] = {
        "fact_id": str(fact.fact_id),
        "text": _render_fact_text(fact, name_by_entity_id),
    }
    if fact.when_active is not None:
        entry["when_active"] = fact.when_active
    return entry


@dataclass
class _MapSnapshotData:
    """Frozen map content for one playthrough's scenario_snapshot, plus the
    designated start pin's entity_id used to seed initial state."""

    maps: list[dict[str, object]] = dataclass_field(default_factory=list)
    pins: list[dict[str, object]] = dataclass_field(default_factory=list)
    connections: list[dict[str, object]] = dataclass_field(default_factory=list)
    start_entity_id: str | None = None


class PlaythroughService:
    """Service orchestrating playthrough creation and retrieval."""

    def __init__(
        self,
        playthrough_repo: PlaythroughRepo,
        participant_repo: ParticipantRepo,
        scenario_repo: ScenarioRepo,
        share_repo: ShareRepo,
        turn_log_repo: TurnLogRepo,
        entity_repo: EntityRepo,
        fact_repo: FactRepo,
        condition_repo: ConditionRepo,
        invariant_repo: InvariantRepo,
        end_condition_repo: EndConditionRepo,
        map_repo: MapRepo,
        minigame_repo: MinigameRepo,
        scenario_music_repo: ScenarioMusicRepo,
        memory_outbox_repo: MemoryOutboxRepo,
        user_repo: UserRepo,
        rule_check_repo: RuleCheckRepo | None = None,
        sheet_rule_repo: SheetRuleRepo | None = None,
        access_repo: ScenarioAccessRepo | None = None,
    ) -> None:
        self.playthrough_repo = playthrough_repo
        self.participant_repo = participant_repo
        self.scenario_repo = scenario_repo
        self.share_repo = share_repo
        self.turn_log_repo = turn_log_repo
        self.entity_repo = entity_repo
        self.fact_repo = fact_repo
        self.condition_repo = condition_repo
        self.invariant_repo = invariant_repo
        self.end_condition_repo = end_condition_repo
        self.map_repo = map_repo
        self.minigame_repo = minigame_repo
        self.scenario_music_repo = scenario_music_repo
        self.memory_outbox_repo = memory_outbox_repo
        self.user_repo = user_repo
        self.rule_check_repo = rule_check_repo or RuleCheckRepo(scenario_repo.session)
        self.sheet_rule_repo = sheet_rule_repo or SheetRuleRepo(scenario_repo.session)
        self.access = ScenarioAccessChecker(
            access_repo or ScenarioAccessRepo(scenario_repo.session)
        )
        self._tool_row_loaders: dict[
            str, Callable[[uuid.UUID], Awaitable[Sequence[object]]]
        ] = {
            "rule_checks": self.rule_check_repo.list_by_scenario,
            "rule_sheet": self.sheet_rule_repo.list_by_scenario,
        }

    async def create_playtest(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
        setup_values: dict[str, object],
        state_overrides: dict[str, object] | None = None,
    ) -> PlaythroughResponse:
        """Start a playtest playthrough of the caller's own scenario.

        Reuses create_playthrough with is_playtest=True so playtest sessions
        run through the exact same pipeline as a real playthrough, but are
        excluded from discovery, play_count, and rating eligibility. Unlike a
        real playthrough, a playtest is allowed on a draft scenario and is
        restricted to the scenario's own creator.
        """
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()
        if scenario.creator_id != user_id:
            raise ScenarioAccessDeniedError()

        return await self.create_playthrough(
            user_id=user_id,
            data=PlaythroughCreate(scenario_id=scenario_id, setup_values=setup_values),
            is_playtest=True,
            state_overrides=state_overrides,
        )

    async def _assert_alpha_run_allowed(
        self, user_id: uuid.UUID, scenario_id: uuid.UUID
    ) -> None:
        if not settings.is_alpha_mode:
            return
        if not await self._is_alpha_playable(scenario_id):
            raise AlphaScenarioOnlyError()
        user = await self.user_repo.get_by_id(user_id)
        if user is None or not is_alpha_consent_current(user):
            raise AlphaConsentRequiredError()

    async def _is_alpha_playable(self, scenario_id: uuid.UUID) -> bool:
        if scenario_id == settings.alpha_scenario_id:
            return True
        visibility = await self.scenario_repo.get_visibility(scenario_id)
        return visibility == PRIVATE_VISIBILITY

    async def create_playthrough(
        self,
        user_id: uuid.UUID,
        data: PlaythroughCreate,
        is_playtest: bool = False,
        state_overrides: dict[str, object] | None = None,
    ) -> PlaythroughResponse:
        """Create a playthrough: snapshot the scenario, seed state, queue memory
        registration. state_overrides presets tracked values and is playtest-only."""
        if state_overrides and not is_playtest:
            raise InvalidStateOverrideError("state_overrides", REASON_PLAYTEST_ONLY)
        await self._assert_alpha_run_allowed(user_id, data.scenario_id)
        scenario = await self.scenario_repo.get_by_id(data.scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()
        await self.access.ensure_can_open(scenario, user_id)
        if not is_playtest and scenario.status != "published":
            raise ScenarioNotPublishedError()
        if scenario.mode == "strategy":
            return await self._create_strategy_playthrough(scenario, user_id, data)
        if data.faction_id is not None:
            raise StrategyFactionRequiredError(
                "faction_id only applies to strategy scenarios"
            )

        _validate_setup_values(scenario.setup_schema, data.setup_values)

        map_data = (
            await self._load_map_data(scenario.scenario_id)
            if scenario.mode == MASTER_MODE
            else None
        )

        # NOTE: Generated here, not left to the ORM column default: SQLAlchemy's
        # `default=uuid.uuid4` on Playthrough.playthrough_id only evaluates at
        # flush/INSERT time, not at object construction, and the Participant
        # below needs the id before either row is flushed.
        playthrough_id = uuid.uuid4()
        snapshot = await self._build_snapshot(scenario, map_data)
        player_entity, setup_facts = _prepare_player_setup(
            scenario.mode,
            scenario.setup_schema,
            data.setup_values,
            snapshot.get("entities", []),  # type: ignore[arg-type]
        )
        opening_scene = _render_opening_scene(scenario, data.setup_values)
        snapshot["opening_scene"] = opening_scene

        playthrough = Playthrough(
            playthrough_id=playthrough_id,
            scenario_id=scenario.scenario_id,
            created_by=user_id,
            state=_with_state_overrides(
                snapshot,
                _build_initial_state(
                    data.setup_values,
                    map_data.start_entity_id if map_data else None,
                    _materialise_snapshot_initials(snapshot, playthrough_id),
                    opening_scene,
                ),
                state_overrides or {},
            ),
            scenario_version=scenario.current_version,
            memory_publish_revision=scenario.publish_revision,
            scenario_snapshot=snapshot,
            is_playtest=is_playtest,
        )
        participant = Participant(
            playthrough_id=playthrough_id,
            user_id=user_id,
            role="owner",
            turn_order_position=1,
        )

        created = await self.playthrough_repo.create(playthrough)
        created_participant = await self.participant_repo.create(participant)
        participants = await self._registration_participants(created_participant)
        if scenario.mode == "newbie":
            player_entity = _newbie_player_entity(
                playthrough_id, scenario.setup_schema, data.setup_values, participants
            )
        await self._enqueue_memory_registration(
            scenario,
            playthrough_id,
            player_entity,
            setup_facts,
            participants,
            _tracked_field_names(scenario, snapshot),
        )
        log_audit_event(
            logger,
            EVENT_PLAYTHROUGH_STARTED,
            playthrough_id=str(playthrough_id),
            scenario_id=str(scenario.scenario_id),
        )
        return _to_response(
            created,
            scenario.title,
            created_participant.participant_id,
            [created_participant],
        )

    async def _create_strategy_playthrough(
        self, scenario: Scenario, user_id: uuid.UUID, data: PlaythroughCreate
    ) -> PlaythroughResponse:
        """Commit the playthrough row first, then ask Simulation for its world."""
        snapshot = await self._build_snapshot(scenario)
        document = StrategyScenario.model_validate(snapshot["strategy_document"])
        faction_id = strategy_playthrough.require_playable_faction(
            document, data.faction_id
        )
        strategy_playthrough.derive_ruler(document, faction_id, data.player_ruler)
        state_dict: dict[str, object] = {
            strategy_playthrough.FACTION_STATE_KEY: faction_id
        }
        if data.player_ruler is not None:
            state_dict["player_ruler"] = data.player_ruler.model_dump(mode="json")
        playthrough = await self.playthrough_repo.create(
            Playthrough(
                playthrough_id=uuid.uuid4(),
                scenario_id=scenario.scenario_id,
                created_by=user_id,
                state={strategy_playthrough.STATE_KEY: state_dict},
                status=INITIALIZING_STATUS,
                scenario_version=scenario.current_version,
                memory_publish_revision=scenario.publish_revision,
                scenario_snapshot=snapshot,
                is_playtest=False,
            )
        )
        participant = await self.participant_repo.create(
            Participant(
                playthrough_id=playthrough.playthrough_id,
                user_id=user_id,
                role="owner",
                turn_order_position=1,
            )
        )
        await self.playthrough_repo.commit()
        return await self._initialize_strategy_world(
            playthrough, scenario.title, participant, player_ruler=data.player_ruler
        )

    async def initialize_playthrough(
        self, playthrough_id: uuid.UUID, user_id: uuid.UUID
    ) -> PlaythroughResponse:
        """Retry world creation for a playthrough stuck in 'initializing'."""
        playthrough = await self.playthrough_repo.get_by_id(playthrough_id)
        if not playthrough:
            raise PlaythroughNotFoundError()
        participant = await self.participant_repo.get_by_playthrough_and_user(
            playthrough_id, user_id
        )
        if not participant:
            raise PlaythroughAccessDeniedError()
        scenario = await self.scenario_repo.get_by_id(playthrough.scenario_id)
        title = scenario.title if scenario else ""
        if playthrough.status != INITIALIZING_STATUS:
            return _to_response(
                playthrough, title, participant.participant_id, [participant]
            )
        return await self._initialize_strategy_world(playthrough, title, participant)

    @staticmethod
    def _persisted_ruler(playthrough: Playthrough) -> PlayerRulerCustomization | None:
        raw = playthrough.state.get(strategy_playthrough.STATE_KEY, {})
        ruler_data = raw.get("player_ruler") if isinstance(raw, dict) else None
        return (
            PlayerRulerCustomization.model_validate(ruler_data) if ruler_data else None
        )

    async def _initialize_strategy_world(
        self,
        playthrough: Playthrough,
        scenario_title: str,
        participant: Participant,
        player_ruler: PlayerRulerCustomization | None = None,
    ) -> PlaythroughResponse:
        document = StrategyScenario.model_validate(
            playthrough.scenario_snapshot["strategy_document"]
        )
        faction_id = playthrough.state[strategy_playthrough.STATE_KEY][
            strategy_playthrough.FACTION_STATE_KEY
        ]
        ruler = player_ruler or self._persisted_ruler(playthrough)
        await simulation_client.initialize_campaign(
            strategy_playthrough.build_initialize_request(
                playthrough.playthrough_id,
                playthrough.created_by,
                document,
                faction_id,
                player_ruler=ruler,
            )
        )
        playthrough.status = ACTIVE_STATUS
        updated = await self.playthrough_repo.update(playthrough)
        log_audit_event(
            logger,
            EVENT_PLAYTHROUGH_STARTED,
            playthrough_id=str(updated.playthrough_id),
            scenario_id=str(updated.scenario_id),
        )
        return _to_response(
            updated, scenario_title, participant.participant_id, [participant]
        )

    async def get_playthrough(
        self, playthrough_id: uuid.UUID, user_id: uuid.UUID
    ) -> PlaythroughResponse:
        """Fetch a playthrough, gated to its participants only."""
        playthrough = await self.playthrough_repo.get_by_id(playthrough_id)
        if not playthrough:
            raise PlaythroughNotFoundError()

        participant = await self.participant_repo.get_by_playthrough_and_user(
            playthrough_id, user_id
        )
        if not participant:
            raise PlaythroughAccessDeniedError()

        scenario = await self.scenario_repo.get_by_id(playthrough.scenario_id)
        scenario_title = scenario.title if scenario else ""
        all_participants = await self.participant_repo.list_by_playthrough(
            playthrough_id
        )
        return _to_response(
            playthrough, scenario_title, participant.participant_id, all_participants
        )

    async def update_character_fields(
        self,
        playthrough_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PlaythroughCharacterUpdate,
    ) -> PlaythroughResponse:
        """Merge edited character setup values into an active playthrough."""
        playthrough = await self.playthrough_repo.get_by_id(playthrough_id)
        if not playthrough:
            raise PlaythroughNotFoundError()

        participant = await self.participant_repo.get_by_playthrough_and_user(
            playthrough_id, user_id
        )
        if not participant:
            raise PlaythroughAccessDeniedError()

        setup_schema = playthrough.scenario_snapshot.get("setup_schema", [])
        _validate_setup_values(setup_schema, data.setup_values)

        merged_setup = {**playthrough.state.get("setup", {}), **data.setup_values}
        playthrough.state = {**playthrough.state, "setup": merged_setup}
        updated = await self.playthrough_repo.update(playthrough)

        scenario = await self.scenario_repo.get_by_id(updated.scenario_id)
        all_participants = await self.participant_repo.list_by_playthrough(
            playthrough_id
        )
        return _to_response(
            updated,
            scenario.title if scenario else "",
            participant.participant_id,
            all_participants,
        )

    async def abandon_playthrough(
        self, playthrough_id: uuid.UUID, user_id: uuid.UUID
    ) -> PlaythroughResponse:
        """Mark an active playthrough as abandoned by its owner."""
        playthrough = await self.playthrough_repo.get_by_id(playthrough_id)
        if not playthrough:
            raise PlaythroughNotFoundError()
        participant = await self.participant_repo.get_by_playthrough_and_user(
            playthrough_id, user_id
        )
        if not participant or participant.role != "owner":
            raise PlaythroughAccessDeniedError()

        playthrough.status = "abandoned"
        updated = await self.playthrough_repo.update(playthrough)
        scenario = await self.scenario_repo.get_by_id(updated.scenario_id)
        all_participants = await self.participant_repo.list_by_playthrough(
            playthrough_id
        )
        return _to_response(
            updated,
            scenario.title if scenario else "",
            participant.participant_id,
            all_participants,
        )

    async def join_playthrough(
        self, share_token: str, user_id: uuid.UUID
    ) -> PlaythroughResponse:
        """Join a playthrough as a multiplayer participant via a join-mode token."""
        if settings.is_alpha_mode:
            raise AlphaFeatureDisabledError()
        share = await self.share_repo.get_by_token(share_token)
        if share is None or share.mode != "join":
            raise InvalidShareTokenError()

        playthrough = await self.playthrough_repo.get_by_id_for_update(
            share.playthrough_id
        )
        if not playthrough:
            raise PlaythroughNotFoundError()
        if playthrough.status != "active":
            raise PlaythroughNotJoinableError()

        scenario = await self.scenario_repo.get_by_id(playthrough.scenario_id)
        if scenario:
            await self.access.ensure_can_open(scenario, user_id)
        if scenario and scenario.player_count_support == "solo":
            raise SoloScenarioJoinError()

        joined_participant = await self._join_as_participant(playthrough, user_id)
        all_participants = await self.participant_repo.list_by_playthrough(
            playthrough.playthrough_id
        )
        return _to_response(
            playthrough,
            scenario.title if scenario else "",
            joined_participant.participant_id,
            all_participants,
        )

    async def _join_as_participant(
        self, playthrough: Playthrough, user_id: uuid.UUID
    ) -> Participant:
        """Add user_id as a participant, no-op if they've already joined."""
        existing = await self.participant_repo.get_by_playthrough_and_user(
            playthrough.playthrough_id, user_id
        )
        if existing:
            return existing
        participants = await self.participant_repo.list_by_playthrough(
            playthrough.playthrough_id
        )
        participant = Participant(
            playthrough_id=playthrough.playthrough_id,
            user_id=user_id,
            role="joined",
            turn_order_position=len(participants) + 1,
        )
        created = await self.participant_repo.create(participant)
        await self._enqueue_memory_participants(playthrough, [*participants, created])
        return created

    async def _enqueue_memory_participants(
        self, playthrough: Playthrough, participants: list[Participant]
    ) -> None:
        """Refresh the names memory attributes actions to; skipped for playthroughs
        that were never registered with memory."""
        if playthrough.memory_publish_revision is None:
            return
        named: list[RegisterParticipant] = []
        for participant in participants:
            named.extend(await self._registration_participants(participant))
        payload = ParticipantsPayload(participants=named)
        await self.memory_outbox_repo.upsert_participants_row(
            playthrough.playthrough_id,
            playthrough.turn_count,
            payload.model_dump(mode="json"),
        )

    async def list_turns(
        self,
        playthrough_id: uuid.UUID,
        user_id: uuid.UUID | None,
        share_token: str | None,
        page: int,
        page_size: int,
        from_turn: int | None,
    ) -> TurnLogListResponse:
        """Fetch paginated turn history. Participants and share-token holders only."""
        playthrough = await self.playthrough_repo.get_by_id(playthrough_id)
        if not playthrough:
            raise PlaythroughNotFoundError()
        await self._require_turns_access(playthrough_id, user_id, share_token)
        state_schema = playthrough.scenario_snapshot.get("state_schema")

        items, total = await self.turn_log_repo.list_by_playthrough(
            playthrough_id,
            limit=page_size,
            offset=(page - 1) * page_size,
            from_turn=from_turn,
        )
        return TurnLogListResponse(
            items=[
                _to_turn_response(
                    item, state_schema if isinstance(state_schema, dict) else {}
                )
                for item in items
            ],
            total_count=total,
        )

    async def _require_turns_access(
        self,
        playthrough_id: uuid.UUID,
        user_id: uuid.UUID | None,
        share_token: str | None,
    ) -> None:
        if user_id is not None:
            participant = await self.participant_repo.get_by_playthrough_and_user(
                playthrough_id, user_id
            )
            if participant:
                return
        if share_token:
            share = await self.share_repo.get_by_token(share_token)
            if share and share.playthrough_id == playthrough_id:
                return
        raise PlaythroughAccessDeniedError()

    async def _enqueue_memory_registration(
        self,
        scenario: Scenario,
        playthrough_id: uuid.UUID,
        player_entity: RegisterPlayerEntity | None,
        setup_facts: list[RegisterSetupFact],
        participants: list[RegisterParticipant],
        tracked_fields: list[str],
    ) -> None:
        payload = RegisterPayload(
            scenario_id=scenario.scenario_id,
            publish_revision=scenario.publish_revision,
            player_entity=player_entity,
            setup_facts=setup_facts,
            participants=participants,
            tracked_fields=tracked_fields,
        )
        await self.memory_outbox_repo.add_register_row(
            playthrough_id, payload.model_dump(mode="json")
        )

    async def _registration_participants(
        self, participant: Participant
    ) -> list[RegisterParticipant]:
        user = await self.user_repo.get_by_id(participant.user_id)
        if user is None or not user.display_name.strip():
            return []
        return [
            RegisterParticipant(
                participant_id=participant.participant_id,
                display_name=user.display_name,
            )
        ]

    async def _build_snapshot(
        self, scenario: Scenario, map_data: _MapSnapshotData | None = None
    ) -> dict[str, object]:
        """Freeze the scenario content TRS and the frontend read for this
        playthrough (ADR-8).

        setup_schema is included alongside the fields ADR-8 names for TRS
        (narrator_persona, state_schema, end_conditions, checkpoints) because
        the same pinning principle applies to it: the play screen displays
        setup field labels from this snapshot, not from Scenario directly, so
        a later edit to the scenario's setup fields doesn't retroactively
        relabel an already-active playthrough. action_chips is pinned for
        the same reason, so a creator's later edit doesn't retroactively
        change the quick-insert chips shown in an already-active playthrough.

        Entities (cards) and the opening scene and mood are pinned in both
        modes. A newbie story keeps its Advanced data stored but pins none of
        it: state_schema, card attribute schemas and tools are empty, so
        switching Advanced mode off is lossless and inert. For master mode,
        also pins facts, rule_invariants, scenario_conditions
        (including their state_mutation column), end_conditions (sorted
        by the creator's explicit priority, ascending — the source of truth
        for end_condition_evaluator's "first match wins" rule,
        master-mode-end-conditions.spec.md), and scenario_minigames (sorted
        by priority ascending, same first-match-wins semantics — the source
        of truth for TRS's minigame_trigger_evaluator,
        master-mode-minigames.spec.md) — TRS never reads Scenario or its
        sub-resource tables directly during a turn
        (master-mode-turn-pipeline.spec.md).

        If the scenario has ≥1 map, also pins maps/map_pins/map_connections
        and injects the two reserved, system-provisioned state_schema fields
        (current_location_id, discovered_location_ids) — a creator never
        authors these directly (app.models.scenario rejects the keys
        unconditionally); TRS's existing entity_ref/list field handling in
        models/game_state.py needs no changes to validate them
        (docs/specs/master-mode-maps.spec.md).
        """
        snapshot: dict[str, object] = {
            "mode": scenario.mode,
            "visibility": scenario.visibility,
            "narrator_persona": scenario.narrator_persona,
            "world_data": scenario.world_data,
            "strategy_document": scenario.strategy_document,
            "setup_schema": scenario.setup_schema,
            "state_schema": _state_schema_for_tools(scenario),
            "checkpoints": scenario.checkpoints,
            "narration_font": scenario.narration_font,
            "narrator_voice_name": scenario.narrator_voice_name,
            "music_tracks": await self._snapshot_music_tracks(scenario.scenario_id),
            "action_chips": scenario.action_chips,
            "entities": await self._snapshot_entities(
                scenario.scenario_id, scenario.mode == MASTER_MODE
            ),
            "opening_scene": scenario.opening_scene,
            "mood_tags": list(scenario.mood_tags),
        }
        narration_limit = narration_limit_from_rules(scenario.rules or {})
        if narration_limit is not None:
            snapshot[SNAPSHOT_KEY_NARRATION_MAX_OUTPUT_TOKENS] = narration_limit
        marker_group = _intent_marker_group_for_mode(scenario)
        if marker_group is not None:
            snapshot[SNAPSHOT_KEY_INTENT_MARKER_GROUP] = marker_group
        tier_tracks = tier_music.resolve_tier_track_urls(
            snapshot["state_schema"]  # type: ignore[arg-type]
        )
        if tier_tracks:
            snapshot["tier_tracks"] = tier_tracks
        if scenario.mode == MASTER_MODE:
            snapshot["facts"] = await self._snapshot_facts(
                scenario.scenario_id,
                snapshot["entities"],  # type: ignore[arg-type]
            )
            snapshot["scenario_conditions"] = await self._snapshot_conditions(
                scenario.scenario_id, scenario.enabled_tools
            )
            snapshot["rule_invariants"] = await self._snapshot_invariants(
                scenario.scenario_id
            )
            snapshot["end_conditions"] = await self._snapshot_end_conditions(
                scenario.scenario_id
            )
            snapshot["scenario_minigames"] = await self._snapshot_minigames(
                scenario.scenario_id, scenario.enabled_tools
            )
            if map_data and map_data.maps:
                snapshot["maps"] = map_data.maps
                snapshot["map_pins"] = map_data.pins
                snapshot["map_connections"] = map_data.connections
                snapshot["state_schema"] = {
                    **_state_schema_for_tools(scenario),
                    _CURRENT_LOCATION_FIELD: {
                        "type": "entity_ref",
                        "entity_type": _LOCATION_ENTITY_TYPE,
                    },
                    _DISCOVERED_LOCATIONS_FIELD: {
                        "type": "list",
                        "item_type": "entity_ref",
                        "entity_type": _LOCATION_ENTITY_TYPE,
                    },
                }
        contributions = await self._snapshot_enabled_tools(scenario)
        extension = contributions.pop(STATE_SCHEMA_EXTENSION_KEY, None)
        if isinstance(extension, dict):
            snapshot["state_schema"] = {**snapshot["state_schema"], **extension}  # type: ignore[dict-item]
        snapshot.update(contributions)
        return snapshot

    async def _snapshot_enabled_tools(self, scenario: Scenario) -> dict[str, object]:
        """Pin the tool list and merge each enabled tool's own snapshot data;
        a disabled tool contributes nothing, which is what makes it inert, and
        a newbie story pins none because its stored tools are switched off."""
        if scenario.mode != MASTER_MODE:
            return {"enabled_tools": []}
        contributions: dict[str, object] = {
            "enabled_tools": list(scenario.enabled_tools)
        }
        for tool_key in scenario.enabled_tools:
            rows = await self._load_tool_rows(tool_key, scenario.scenario_id)
            contributions.update(contribute_snapshot(tool_key, scenario, rows))
        return contributions

    async def _load_tool_rows(
        self, tool_key: str, scenario_id: uuid.UUID
    ) -> Sequence[object]:
        loader = self._tool_row_loaders.get(tool_key)
        if loader is None:
            return []
        return await loader(scenario_id)

    async def _snapshot_entities(
        self, scenario_id: uuid.UUID, has_card_values: bool
    ) -> list[dict[str, object]]:
        entities = await self.entity_repo.list_by_scenario(scenario_id)
        return [
            {
                "entity_id": str(e.entity_id),
                "entity_type": e.entity_type,
                "canonical_name": e.canonical_name,
                "aliases": e.aliases,
                "description": e.description,
                "attributes_schema": e.attributes_schema if has_card_values else {},
                "obtainable": e.obtainable,
                "narrator_instruction": e.narrator_instruction,
                "is_player": e.is_player,
            }
            for e in entities
        ]

    async def _snapshot_facts(
        self, scenario_id: uuid.UUID, entities_snapshot: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        """Pins non-hidden facts at playthrough creation, same rationale as
        _snapshot_entities (ADR-8). Previously omitted entirely -- master-mode
        playthroughs had authored facts nowhere in scenario_snapshot, so the
        play screen's Codex could never show them, unlike entities."""
        name_by_entity_id = {
            str(e["entity_id"]): str(e["canonical_name"]) for e in entities_snapshot
        }
        facts = await self.fact_repo.list_by_scenario(scenario_id)
        return [_snapshot_fact(f, name_by_entity_id) for f in facts if not f.hidden]

    async def _load_map_data(self, scenario_id: uuid.UUID) -> _MapSnapshotData:
        """Freeze every map/pin/connection for this scenario at playthrough
        creation (ADR-8) and locate the designated start pin's entity_id."""
        maps = await self.map_repo.list_maps_by_scenario(scenario_id)
        if not maps:
            return _MapSnapshotData()

        all_pins = await self.map_repo.list_pins_by_scenario(scenario_id)
        pins_by_map_id: dict[uuid.UUID, list[MapPin]] = {}
        for pin in all_pins:
            pins_by_map_id.setdefault(pin.map_id, []).append(pin)

        pins: list[dict[str, object]] = []
        start_entity_id: str | None = None
        for scenario_map in maps:
            for pin in pins_by_map_id.get(scenario_map.map_id, []):
                pins.append(
                    {
                        "map_id": str(pin.map_id),
                        "entity_id": str(pin.entity_id),
                        "x": pin.x,
                        "y": pin.y,
                        "is_start_location": pin.is_start_location,
                    }
                )
                if pin.is_start_location:
                    start_entity_id = str(pin.entity_id)

        connections = await self.map_repo.list_connections_by_scenario(scenario_id)
        return _MapSnapshotData(
            maps=[
                {
                    "map_id": str(m.map_id),
                    "name": m.name,
                    "image_url": m.image_url,
                }
                for m in maps
            ],
            pins=pins,
            connections=[
                {
                    "entity_id_a": str(c.entity_id_a),
                    "entity_id_b": str(c.entity_id_b),
                    "label": c.label,
                }
                for c in connections
            ],
            start_entity_id=start_entity_id,
        )

    async def _snapshot_music_tracks(self, scenario_id: uuid.UUID) -> dict[str, str]:
        """Pin a real, always-playable track URL for each of the 6 mood
        slots: an explicit upload/generated track, or the canonical built-in
        default for an untouched slot or an explicit 'use default' selection.
        Also the sole source of music_tracks for newbie-mode scenarios,
        which never write scenario_music rows -- every mood there falls
        through to the built-in default."""
        rows = await self.scenario_music_repo.get_by_scenario(scenario_id)
        rows_by_mood = {row.mood: row for row in rows}
        result: dict[str, str] = {}
        for mood in MOOD_SLOTS:
            row = rows_by_mood.get(mood)
            if row is not None and row.source != "default" and row.track_url:
                result[mood] = row.track_url
            else:
                result[mood] = default_music.default_track_url(mood)
        return result

    async def _snapshot_conditions(
        self, scenario_id: uuid.UUID, enabled_tools: Sequence[str]
    ) -> list[dict[str, object]]:
        conditions = await self.condition_repo.list_by_scenario(scenario_id)
        has_cues = "atmosphere" in enabled_tools
        return [
            {
                "condition_id": str(c.condition_id),
                "label": c.label,
                "condition_expression": c.condition_expression,
                "narrator_instruction": c.narrator_instruction,
                "state_mutation": c.state_mutation,
                "state_mutations": list(c.state_mutations),
                "is_one_shot": c.is_one_shot,
                "metadata": c.metadata_,
                **(_cue_fields(c) if has_cues else {}),
            }
            for c in conditions
        ]

    async def _snapshot_end_conditions(
        self, scenario_id: uuid.UUID
    ) -> list[dict[str, object]]:
        end_conditions = await self.end_condition_repo.list_by_scenario(scenario_id)
        return [
            {
                "end_condition_id": str(ec.end_condition_id),
                "condition_expression": ec.condition_expression,
                "outcome_tag": ec.outcome_tag,
                "outcome_title": ec.outcome_title,
                "outcome_text": ec.outcome_text,
                "is_secret": ec.is_secret,
                "priority": ec.priority,
            }
            for ec in end_conditions
        ]

    async def _snapshot_minigames(
        self, scenario_id: uuid.UUID, enabled_tools: Sequence[str] = ()
    ) -> list[dict[str, object]]:
        """Composure minigames are inert data while their tool is off: kept in the
        scenario, absent from the pinned snapshot."""
        is_composure_on = COMPOSURE_TOOL_KEY in enabled_tools
        minigames = await self.minigame_repo.list_by_scenario(scenario_id)
        return [
            {
                "minigame_id": str(m.minigame_id),
                "label": m.label,
                "minigame_type": m.minigame_type,
                "trigger_condition_expression": m.trigger_condition_expression,
                "priority": m.priority,
                "outcome_mode": m.outcome_mode,
                "win_mutation": m.win_mutation,
                "lose_mutation": m.lose_mutation,
                "win_mutations": list(m.win_mutations),
                "lose_mutations": list(m.lose_mutations),
                "tiered_outcomes": m.tiered_outcomes,
                "timeout_mutation": m.timeout_mutation,
                "timeout_mutations": list(m.timeout_mutations),
                "narrator_instruction_template": m.narrator_instruction_template,
                # NOTE: Parse persisted legacy JSON through the config model before
                # freezing it into a playthrough snapshot. This gives old
                # scenarios all current safe defaults while retaining every
                # nested authoring setting in the runtime event path.
                "dodge_config": (
                    DodgeConfig.model_validate(m.dodge_config).model_dump(mode="json")
                    if m.minigame_type == "dodge" and m.dodge_config is not None
                    else m.dodge_config
                ),
                "lockpick_config": (
                    LockpickConfig.model_validate(m.lockpick_config).model_dump(
                        mode="json"
                    )
                    if m.minigame_type == "lockpick" and m.lockpick_config is not None
                    else m.lockpick_config
                ),
                "composure_config": (
                    ComposureConfig.model_validate(m.composure_config).model_dump(
                        mode="json"
                    )
                    if m.minigame_type == COMPOSURE_TYPE
                    and m.composure_config is not None
                    else m.composure_config
                ),
            }
            for m in minigames
            if m.minigame_type != COMPOSURE_TYPE or is_composure_on
        ]

    async def _snapshot_invariants(
        self, scenario_id: uuid.UUID
    ) -> list[dict[str, object]]:
        invariants = await self.invariant_repo.list_by_scenario(scenario_id)
        return [
            {
                "label": i.label,
                "invariant_expression": i.invariant_expression,
                "applies_to": i.applies_to,
                "narrator_text": i.narrator_text,
            }
            for i in invariants
        ]


def _validate_setup_values(
    setup_schema: list[object], setup_values: dict[str, object]
) -> None:
    """Validate submitted setup values against the scenario's setup_schema."""
    for field in setup_schema:
        if not isinstance(field, dict):
            continue
        _validate_single_field(field, setup_values)


def _validate_single_field(
    field: dict[str, object], setup_values: dict[str, object]
) -> None:
    """Validate a single setup schema field against submitted values."""
    field_key = str(field.get("field_key") or field.get("key") or field.get("id") or "")
    if not field_key:
        return
    is_required = bool(field.get("required", False))
    val = setup_values.get(field_key)

    if is_required and (val is None or val == "" or val == []):
        raise InvalidSetupValuesError(f"Missing required setup field: {field_key}")

    if val is None or val == "":
        return

    field_type = str(field.get("type") or "")
    if field_type in ("select", "single_select"):
        _validate_select_field(field_key, val, field.get("options"))
    elif field_type == "multi_select":
        _validate_multi_select_field(field_key, val, field.get("options"))


def _extract_option_values(options_raw: object) -> list[str]:
    """Extract string values from option list (strings or dicts)."""
    if not isinstance(options_raw, list):
        return []
    valid: list[str] = []
    for opt in options_raw:
        if isinstance(opt, str):
            valid.append(opt)
        elif isinstance(opt, dict) and "value" in opt:
            valid.append(str(opt["value"]))
    return valid


def _validate_select_field(field_key: str, val: object, options_raw: object) -> None:
    """Validate single-select value against options."""
    valid_options = _extract_option_values(options_raw)
    if valid_options and str(val) not in valid_options:
        raise InvalidSetupValuesError(
            f"Invalid value for setup field {field_key!r}: must be one of {valid_options}"
        )


def _validate_multi_select_field(
    field_key: str, val: object, options_raw: object
) -> None:
    """Validate multi-select array value against options."""
    valid_options = _extract_option_values(options_raw)
    if not valid_options:
        return
    selected = val if isinstance(val, list) else [val]
    for item in selected:
        if str(item) not in valid_options:
            raise InvalidSetupValuesError(
                f"Invalid selection {item!r} for setup field {field_key!r}"
            )


def _intent_marker_group_for_mode(scenario: Scenario) -> str | None:
    if scenario.mode != MASTER_MODE:
        return None
    return intent_marker_group_from_rules(
        scenario.rules or {}, scenario.state_schema or {}
    )


def _state_schema_for_tools(scenario: Scenario) -> dict[str, object]:
    """Tool-owned field settings are inert while their tool is off: display
    hints (`status_hud`) and `initial_random` (`rule_checks`) stay in the
    scenario and are absent from the pinned schema."""
    if scenario.mode != MASTER_MODE:
        return {}
    schema = scenario.state_schema
    if STATUS_HUD_TOOL_KEY not in scenario.enabled_tools:
        schema = strip_display_hints(schema)
    if RULE_CHECKS_TOOL_KEY not in scenario.enabled_tools:
        schema = strip_initial_random(schema)
    return schema


def _to_turn_response(
    turn_log: TurnLog, state_schema: dict[str, object]
) -> TurnLogResponse:
    """A turn as scrollback returns it: tool calls aimed at hidden state fields
    are dropped so the log cannot reveal what `hidden` conceals."""
    response = TurnLogResponse.model_validate(turn_log)
    kept = redact_hidden_tool_calls(
        [call.model_dump() for call in response.tool_calls], state_schema
    )
    return response.model_copy(
        update={"tool_calls": [ToolCallLogEntry(**call) for call in kept]}
    )


def _cue_fields(condition: ScenarioCondition) -> dict[str, object]:
    return {
        "sensory_cue": condition.sensory_cue,
        "cut_ambient": condition.cut_ambient,
        "silence_duration_ms": condition.silence_duration_ms,
    }


def _materialise_snapshot_initials(
    snapshot: dict[str, object], playthrough_id: uuid.UUID
) -> dict[str, object]:
    state_schema = snapshot.get("state_schema")
    entities = snapshot.get("entities")
    enabled_tools = snapshot.get("enabled_tools")
    return materialise_initial_state(
        state_schema if isinstance(state_schema, dict) else {},
        entities if isinstance(entities, list) else [],
        random.Random(int.from_bytes(playthrough_id.bytes, "big")),
        enabled_tools if isinstance(enabled_tools, list) else [],
    )


def _with_state_overrides(
    snapshot: dict[str, object],
    state: dict[str, object],
    state_overrides: dict[str, object],
) -> dict[str, object]:
    if not state_overrides:
        return state
    state_schema = snapshot.get("state_schema")
    entities = snapshot.get("entities")
    validated = validate_state_overrides(
        state_schema if isinstance(state_schema, dict) else {},
        entities if isinstance(entities, list) else [],
        state_overrides,
    )
    return merge_state_overrides(state, validated)


def _chosen_character_name(scenario: Scenario, setup_values: dict[str, object]) -> str:
    name_key = _extract_name_field_key(scenario.setup_schema)
    chosen = setup_values.get("character_name") or setup_values.get(name_key or "")
    return str(chosen or "")


def _render_opening_scene(
    scenario: Scenario, setup_values: dict[str, object]
) -> str | None:
    return render_opening_scene(
        scenario.opening_scene, _chosen_character_name(scenario, setup_values)
    )


def _build_initial_state(
    setup_values: dict[str, object],
    start_location_entity_id: str | None,
    seeded_initials: dict[str, object] | None = None,
    opening_prompt: str | None = None,
) -> dict[str, object]:
    """Seed Playthrough.state: schema initials, then opening prompt + setup
    values for every mode (these win on conflict), plus the reserved
    current_location_id/discovered_location_ids fields when the scenario has
    a designated start pin (master mode with maps)."""
    state: dict[str, object] = {
        **(seeded_initials or {}),
        "setup": dict(setup_values),
        "narrative": {"opening_prompt": opening_prompt},
    }
    if start_location_entity_id:
        state[_CURRENT_LOCATION_FIELD] = start_location_entity_id
        state[_DISCOVERED_LOCATIONS_FIELD] = [start_location_entity_id]
    return state


def _to_response(
    playthrough: Playthrough,
    scenario_title: str,
    participant_id: uuid.UUID,
    participants: list[Participant],
) -> PlaythroughResponse:
    """Map a Playthrough ORM entity to its response schema; the only place a
    snapshot or state leaves the service, so hidden fields are filtered here."""
    snapshot = playthrough.scenario_snapshot
    state_schema = snapshot.get("state_schema")
    return PlaythroughResponse(
        playthrough_id=playthrough.playthrough_id,
        scenario_id=playthrough.scenario_id,
        scenario_title=scenario_title,
        created_by=playthrough.created_by,
        state=visible_state(
            playthrough.state, state_schema if isinstance(state_schema, dict) else {}
        ),
        checkpoint=playthrough.checkpoint,
        turn_count=playthrough.turn_count,
        status=playthrough.status,
        ended_outcome_tag=playthrough.ended_outcome_tag,
        ended_outcome_title=playthrough.ended_outcome_title,
        ended_outcome_text=playthrough.ended_outcome_text,
        is_playtest=playthrough.is_playtest,
        scenario_version=playthrough.scenario_version,
        scenario_snapshot=client_snapshot(snapshot),
        server_time_ms=time.time_ns() // NANOSECONDS_PER_MILLISECOND,
        rule_sheet=_rule_sheet_items(snapshot, playthrough.state),
        created_at=playthrough.created_at,
        updated_at=playthrough.updated_at,
        participant_id=participant_id,
        participants=[ParticipantSummary.model_validate(p) for p in participants],
        active_conditions=list_active_condition_labels(
            playthrough.scenario_snapshot.get("scenario_conditions", []),
            playthrough.state,
            state_schema if isinstance(state_schema, dict) else None,
        ),
    )


def _rule_sheet_items(
    snapshot: dict[str, object], state: dict[str, object]
) -> list[RuleSheetItem]:
    sheet_rules = snapshot.get("sheet_rules")
    if not isinstance(sheet_rules, list):
        return []
    rule_status = state.get(RULE_STATUS_ROOT)
    view = rule_sheet_view(
        [rule for rule in sheet_rules if isinstance(rule, dict)],
        rule_status if isinstance(rule_status, dict) else {},
    )
    return [RuleSheetItem(**item) for item in view]


def _extract_name_field_key(setup_schema: list[object]) -> str | None:
    """Find the key of the field designated as the character name."""
    for field in setup_schema:
        if not isinstance(field, dict):
            continue
        if field.get("is_character_name"):
            return str(field.get("key") or field.get("field_key") or "")
        key = str(field.get("key") or field.get("field_key") or "")
        if key in ("character_name", "characterName", "name"):
            return key
    return None


def _schema_field_names(schema: object) -> set[str]:
    """Top-level keys plus the keys of nested `fields` objects of a state schema."""
    if not isinstance(schema, dict):
        return set()
    names = set(schema)
    for definition in schema.values():
        if isinstance(definition, dict):
            names |= _schema_field_names(definition.get("fields"))
    return names


def _tracked_field_names(scenario: Scenario, snapshot: dict[str, object]) -> list[str]:
    """Attribute and state field names the game tracks itself, so memory never
    extracts them from prose. Master mode only."""
    if scenario.mode != MASTER_MODE:
        return []
    names = _schema_field_names(scenario.state_schema)
    entities = snapshot.get("entities", [])
    for entity in entities if isinstance(entities, list) else []:
        if isinstance(entity, dict):
            names |= _schema_field_names(entity.get("attributes_schema"))
    return sorted(names)


def _format_fact_object(val: object) -> str:
    """Format a setup value as an object string for a fact."""
    if isinstance(val, list):
        return ", ".join(str(item) for item in val)
    return str(val)


def _build_setup_facts(
    setup_schema: list[object],
    setup_values: dict[str, object],
    subject_id: uuid.UUID,
    name_field_key: str | None,
) -> list[RegisterSetupFact]:
    """Generate ground-truth facts for custom setup choices."""
    facts: list[RegisterSetupFact] = []
    for field in setup_schema:
        if not isinstance(field, dict):
            continue
        key = str(field.get("key") or field.get("field_key") or "")
        if not key or key == name_field_key or key not in setup_values:
            continue
        val = setup_values[key]
        if val is None or val == "" or val == []:
            continue
        predicate = str(field.get("predicate") or f"has_{key}")
        facts.append(
            RegisterSetupFact(
                fact_id=uuid.uuid4(),
                subject_entity_id=subject_id,
                predicate=predicate,
                object_literal=_format_fact_object(val),
            )
        )
    return facts


def _newbie_player_entity(
    playthrough_id: uuid.UUID,
    setup_schema: list[object],
    setup_values: dict[str, object],
    participants: list[RegisterParticipant],
) -> RegisterPlayerEntity:
    """Newbie scenarios author no player entity, so memory gets one per playthrough.

    Without it, extraction has no entity to attribute the player's own actions and
    commitments to.
    """
    name_key = _extract_name_field_key(setup_schema)
    chosen_name = str(setup_values.get(name_key or "", "")).strip() if name_key else ""
    display_name = participants[0].display_name.strip() if participants else ""
    canonical_name = chosen_name or display_name or FALLBACK_PLAYER_NAME
    aliases = [display_name] if display_name and display_name != canonical_name else []
    return RegisterPlayerEntity(
        authored_entity_id=uuid.uuid5(playthrough_id, NEWBIE_PLAYER_ENTITY_KEY),
        canonical_name=canonical_name,
        aliases=aliases,
        entity_type=NEWBIE_PLAYER_ENTITY_TYPE,
    )


def _find_player_entity(
    snapshot_entities: list[dict[str, object]],
) -> dict[str, object] | None:
    return next(
        (e for e in snapshot_entities if isinstance(e, dict) and e.get("is_player")),
        None,
    )


def _apply_chosen_player_name(
    player_ent: dict[str, object], raw_name: str, setup_values: dict[str, object]
) -> None:
    """Rewrite the snapshot's player entity and setup values with the chosen name."""
    default_name = str(player_ent.get("canonical_name") or "")
    chosen_name = raw_name or default_name
    aliases = list(player_ent.get("aliases") or [])  # type: ignore[arg-type]
    if raw_name and default_name != raw_name and default_name not in aliases:
        aliases.insert(0, default_name)
    player_ent["canonical_name"] = chosen_name
    player_ent["aliases"] = aliases
    setup_values["character_name"] = chosen_name
    setup_values["player_entity_id"] = str(player_ent["entity_id"])


def _prepare_player_setup(
    scenario_mode: str,
    setup_schema: list[object],
    setup_values: dict[str, object],
    snapshot_entities: list[dict[str, object]],
) -> tuple[RegisterPlayerEntity | None, list[RegisterSetupFact]]:
    """Resolve custom player character name and facts from setup values."""
    player_ent = _find_player_entity(snapshot_entities)
    if scenario_mode != MASTER_MODE or not player_ent:
        return None, []

    subject_id = uuid.UUID(str(player_ent["entity_id"]))
    name_key = _extract_name_field_key(setup_schema)
    raw_name = str(setup_values.get(name_key or "", "")).strip() if name_key else ""
    _apply_chosen_player_name(player_ent, raw_name, setup_values)

    facts = _build_setup_facts(setup_schema, setup_values, subject_id, name_key)
    player_entity = RegisterPlayerEntity(
        authored_entity_id=subject_id,
        canonical_name=str(player_ent["canonical_name"]),
        aliases=list(player_ent["aliases"]),  # type: ignore[call-overload]
        entity_type=str(player_ent["entity_type"]),
    )
    return player_entity, facts
