"""Scenario domain service handling business logic, access rules, and versioning."""

import copy
import uuid

import structlog
from app.config import settings
from app.db.models.end_condition import EndCondition
from app.db.models.entity import Entity
from app.db.models.fact import Fact
from app.db.models.map_connection import MapConnection
from app.db.models.map_pin import MapPin
from app.db.models.review import ScenarioReview
from app.db.models.rule_invariant import RuleInvariant
from app.db.models.scenario import Scenario
from app.db.models.scenario_condition import ScenarioCondition
from app.db.models.scenario_entity_type import ScenarioEntityType
from app.db.models.scenario_map import ScenarioMap
from app.db.models.scenario_minigame import ScenarioMinigame
from app.db.models.scenario_music import ScenarioMusic
from app.db.models.scenario_rule_check import ScenarioRuleCheck
from app.db.models.scenario_sheet_rule import ScenarioSheetRule
from app.exceptions.memory_exceptions import MemoryPurgeError
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioModeLockedError,
    ScenarioNotFoundError,
    ScenarioValidationError,
)
from app.integrations import memory_client
from app.models.review import (
    PublicPlaythroughSummary,
    RatingCountResponse,
    ScenarioReviewCreate,
    ScenarioReviewListResponse,
    ScenarioReviewResponse,
)
from app.models.scenario import (
    MyScenarioListResponse,
    MyScenarioSummary,
    ScenarioCreate,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioStatusCounts,
    ScenarioSummaryResponse,
    ScenarioUpdate,
)
from app.repositories.condition_repo import ConditionRepo
from app.repositories.end_condition_repo import EndConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.invariant_repo import InvariantRepo
from app.repositories.map_repo import MapRepo
from app.repositories.minigame_repo import MinigameRepo
from app.repositories.rule_check_repo import RuleCheckRepo
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_entity_type_repo import ScenarioEntityTypeRepo
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.repositories.scenario_repo import (
    ARCHIVED_STATUSES,
    DRAFT_STATUSES,
    PUBLISHED_TAB_STATUSES,
    ScenarioListFilters,
    ScenarioRepo,
)
from app.repositories.sheet_rule_repo import SheetRuleRepo
from app.services.display_hints import validate_display_hints
from app.services.rule_sheet_state import validate_reserved_roots
from app.services.scenario_access import ScenarioAccessChecker, is_private
from app.services.scenario_documents import apply_rendered_documents
from app.services.scenario_edit_guard import ensure_not_publishing, ensure_not_stale
from app.services.schema_field_validation import validate_schema_fields

logger = structlog.get_logger()

EVENT_MEMORY_PURGE_FAILED = "memory_purge_failed"

STUDIO_TAB_STATUSES: dict[str, tuple[str, ...]] = {
    "drafts": DRAFT_STATUSES,
    "published": PUBLISHED_TAB_STATUSES,
    "archived": ARCHIVED_STATUSES,
}
STUDIO_LIST_SORT = "edited"
ANONYMOUS_CREATOR_NAME = "Anonymous Creator"
MIN_TURNS_TO_REVIEW = 10
STAR_RATINGS_DESCENDING = (5, 4, 3, 2, 1)

MODE_NEWBIE = "newbie"
MODE_MASTER = "master"
MODE_STRATEGY = "strategy"
DEFAULT_TIER_BY_MODE: dict[str, str] = {
    MODE_NEWBIE: "newbie",
    MODE_MASTER: "intermediate",
    MODE_STRATEGY: "master",
}

STORY_SCHEMA_FIELDS: set[str] = {
    "mode",
    "narrator_persona",
    "world_data",
    "strategy_document",
    "setup_schema",
    "state_schema",
    "end_conditions",
    "checkpoints",
    "rules",
    "opening_scene",
    "narration_font",
    "narrator_voice_name",
    "action_chips",
    "setup_archetypes",
    "mood_tags",
    "narrator_persona_document",
    "player_mode",
}


def _to_review_response(
    review: ScenarioReview, display_name: str
) -> ScenarioReviewResponse:
    return ScenarioReviewResponse(
        review_id=review.review_id,
        scenario_id=review.scenario_id,
        user_id=review.user_id,
        user_display_name=display_name,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


def _alpha_scenario_filter() -> uuid.UUID | None:
    return settings.alpha_scenario_id if settings.is_alpha_mode else None


def _is_hidden_by_alpha_mode(scenario: Scenario) -> bool:
    """In alpha mode only the alpha scenario and private scenarios are reachable;
    a private one is then still gated by its own allowlist."""
    if not settings.is_alpha_mode or is_private(scenario):
        return False
    return scenario.scenario_id != settings.alpha_scenario_id


def _next_cursor(offset: int, limit: int, total_count: int) -> str | None:
    next_offset = offset + limit
    return str(next_offset) if next_offset < total_count else None


async def _purge_scenario_memory_best_effort(scenario_id: uuid.UUID) -> None:
    """A failed purge never blocks the delete; reconcile cleans the orphan later."""
    try:
        await memory_client.purge(scenario_ids=[scenario_id])
    except MemoryPurgeError as error:
        logger.warning(
            EVENT_MEMORY_PURGE_FAILED,
            scenario_id=str(scenario_id),
            code=error.code,
            upstream_status=error.upstream_status,
        )


def _apply_mode_switch(scenario: Scenario, update_dict: dict[str, object]) -> None:
    """Moves the complexity tier with the mode only while it still sits on the
    previous mode's default, so a tier the creator chose is never overwritten."""
    new_mode = update_dict.get("mode")
    if new_mode is None or new_mode == scenario.mode:
        update_dict.pop("mode", None)
        return
    if scenario.mode == MODE_STRATEGY:
        raise ScenarioModeLockedError()
    is_tier_requested = "complexity_tier" in update_dict
    is_on_default_tier = scenario.complexity_tier == DEFAULT_TIER_BY_MODE[scenario.mode]
    if not is_tier_requested and is_on_default_tier:
        update_dict["complexity_tier"] = DEFAULT_TIER_BY_MODE[str(new_mode)]


def _validate_strategy_document_for_mode(mode: str, document: object) -> None:
    if not isinstance(document, dict):
        raise ScenarioValidationError("strategy_document must be an object")
    if mode == MODE_STRATEGY and not document:
        raise ScenarioValidationError("strategy_document is required for strategy mode")
    if mode != MODE_STRATEGY and document:
        raise ScenarioValidationError(
            "strategy_document is only valid for strategy mode"
        )


def _has_unpublished_changes(scenario: Scenario) -> bool:
    if scenario.status != "published" or scenario.published_content_edited_at is None:
        return False
    return scenario.content_edited_at > scenario.published_content_edited_at


def _to_status_counts(counts_by_status: dict[str, int]) -> ScenarioStatusCounts:
    def total_for(statuses: tuple[str, ...]) -> int:
        return sum(counts_by_status.get(status, 0) for status in statuses)

    return ScenarioStatusCounts(
        all=sum(counts_by_status.values()),
        drafts=total_for(DRAFT_STATUSES),
        published=total_for(PUBLISHED_TAB_STATUSES),
        archived=total_for(ARCHIVED_STATUSES),
    )


class ScenarioService:
    """Service handling high-level scenario workflow logic."""

    def __init__(
        self,
        scenario_repo: ScenarioRepo,
        entity_repo: EntityRepo | None = None,
        fact_repo: FactRepo | None = None,
        condition_repo: ConditionRepo | None = None,
        end_condition_repo: EndConditionRepo | None = None,
        invariant_repo: InvariantRepo | None = None,
        entity_type_repo: ScenarioEntityTypeRepo | None = None,
        map_repo: MapRepo | None = None,
        minigame_repo: MinigameRepo | None = None,
        music_repo: ScenarioMusicRepo | None = None,
        rule_check_repo: RuleCheckRepo | None = None,
        sheet_rule_repo: SheetRuleRepo | None = None,
        access_repo: ScenarioAccessRepo | None = None,
    ) -> None:
        self.scenario_repo = scenario_repo
        # NOTE: Sub-resource repos are optional constructor args (rather than
        # required) so every existing call site that only ever needed
        # scenario CRUD (most of the codebase and its tests) is unaffected;
        # they're only exercised by duplicate_scenario. Built from the same
        # session scenario_repo already holds, per the "repositories are the
        # only place that opens SQL" layering rule.
        session = scenario_repo.session
        self.entity_repo = entity_repo or EntityRepo(session)
        self.fact_repo = fact_repo or FactRepo(session)
        self.condition_repo = condition_repo or ConditionRepo(session)
        self.end_condition_repo = end_condition_repo or EndConditionRepo(session)
        self.invariant_repo = invariant_repo or InvariantRepo(session)
        self.entity_type_repo = entity_type_repo or ScenarioEntityTypeRepo(session)
        self.map_repo = map_repo or MapRepo(session)
        self.minigame_repo = minigame_repo or MinigameRepo(session)
        self.music_repo = music_repo or ScenarioMusicRepo(session)
        self.rule_check_repo = rule_check_repo or RuleCheckRepo(session)
        self.sheet_rule_repo = sheet_rule_repo or SheetRuleRepo(session)
        self.access = ScenarioAccessChecker(access_repo or ScenarioAccessRepo(session))

    async def create_scenario(
        self, user_id: uuid.UUID, data: ScenarioCreate
    ) -> ScenarioResponse:
        """Create a new draft scenario owned by user_id."""
        validate_display_hints(data.state_schema, [])
        validate_schema_fields(data.state_schema, [])
        validate_reserved_roots(data.state_schema, [])
        _validate_strategy_document_for_mode(data.mode, data.strategy_document)
        fields = data.model_dump()
        apply_rendered_documents(fields)
        scenario = Scenario(
            **fields, creator_id=user_id, status="draft", current_version=1
        )
        created_scenario = await self.scenario_repo.create(scenario)
        return ScenarioResponse.model_validate(created_scenario)

    async def get_scenario(
        self, scenario_id: uuid.UUID, current_user_id: uuid.UUID | None = None
    ) -> ScenarioResponse:
        """Fetch scenario by ID; never-published scenarios are creator-only."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()
        if _is_hidden_by_alpha_mode(scenario):
            raise ScenarioNotFoundError()
        await self.access.ensure_can_open(scenario, current_user_id)

        # NOTE: Gate on published_at, not status: a first publish sits in
        # 'publishing' with unpublished content, while a re-publish (or a
        # failed one) of a live scenario must stay publicly readable.
        if scenario.published_at is None:
            self._ensure_creator_access(scenario, current_user_id, hide_as_404=True)

        response = ScenarioResponse.model_validate(scenario)
        if scenario.creator_id != current_user_id:
            response.publish_error = None
            response.guide_seen_features = []
        await self._apply_creator_fields(response, scenario)
        await self._apply_viewer_fields(response, scenario_id, current_user_id)
        await self._apply_mechanics_flags(response, scenario_id)
        return response

    async def _apply_creator_fields(
        self, response: ScenarioResponse, scenario: Scenario
    ) -> None:
        creator = await self.scenario_repo.get_creator_card(scenario.creator_id)
        response.creator_display_name = (
            creator.display_name if creator else None
        ) or ANONYMOUS_CREATOR_NAME
        if creator:
            response.creator_avatar_url = creator.avatar_url
            response.creator_bio = creator.bio
        response.creator_other_scenarios_count = (
            await self.scenario_repo.count_other_published_by_creator(
                scenario.creator_id, scenario.scenario_id
            )
        )

    async def _apply_viewer_fields(
        self,
        response: ScenarioResponse,
        scenario_id: uuid.UUID,
        current_user_id: uuid.UUID | None,
    ) -> None:
        if not current_user_id:
            return
        response.is_bookmarked = await self.scenario_repo.is_bookmarked(
            current_user_id, scenario_id
        )
        response.can_review = await self.scenario_repo.has_user_played_min_turns(
            current_user_id, scenario_id, min_turns=MIN_TURNS_TO_REVIEW
        )

    async def _apply_mechanics_flags(
        self, response: ScenarioResponse, scenario_id: uuid.UUID
    ) -> None:
        response.has_maps = await self.map_repo.count_maps_by_scenario(scenario_id) > 0
        response.has_minigames = (
            await self.minigame_repo.count_by_scenario(scenario_id) > 0
        )

    async def toggle_bookmark(self, user_id: uuid.UUID, scenario_id: uuid.UUID) -> bool:
        """Toggle scenario bookmark for user. Returns new bookmarked state."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()
        await self.access.ensure_can_open(scenario, user_id)

        is_currently_bookmarked = await self.scenario_repo.is_bookmarked(
            user_id, scenario_id
        )
        if is_currently_bookmarked:
            await self.scenario_repo.remove_bookmark(user_id, scenario_id)
            return False
        await self.scenario_repo.add_bookmark(user_id, scenario_id)
        return True

    async def list_reviews(
        self,
        scenario_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        current_user_id: uuid.UUID | None = None,
    ) -> ScenarioReviewListResponse:
        """Fetch a page of reviews plus all-review star counts and the viewer's own."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()
        await self.access.ensure_can_open(scenario, current_user_id)

        items, total_count, avg_rating = await self.scenario_repo.list_reviews(
            scenario_id, limit, offset
        )
        rating_counts = await self.scenario_repo.get_rating_counts(scenario_id)
        return ScenarioReviewListResponse(
            items=[_to_review_response(rev, name) for rev, name in items],
            total_count=total_count,
            average_rating=avg_rating,
            rating_counts=[
                RatingCountResponse(stars=stars, count=rating_counts.get(stars, 0))
                for stars in STAR_RATINGS_DESCENDING
            ],
            own_review=await self._get_own_review(scenario_id, current_user_id),
        )

    async def _get_own_review(
        self, scenario_id: uuid.UUID, current_user_id: uuid.UUID | None
    ) -> ScenarioReviewResponse | None:
        if not current_user_id:
            return None
        own = await self.scenario_repo.get_user_review(current_user_id, scenario_id)
        return _to_review_response(*own) if own else None

    async def add_review(
        self, user_id: uuid.UUID, scenario_id: uuid.UUID, data: ScenarioReviewCreate
    ) -> ScenarioReviewResponse:
        """Submit a rating and review after validating user has played >= 10 turns."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()
        await self.access.ensure_can_open(scenario, user_id)

        has_min_turns = await self.scenario_repo.has_user_played_min_turns(
            user_id, scenario_id, min_turns=MIN_TURNS_TO_REVIEW
        )
        if not has_min_turns:
            raise ScenarioAccessDeniedError(
                "You must play at least 10 turns of this scenario before leaving a review."
            )

        review, display_name = await self.scenario_repo.create_or_update_review(
            user_id=user_id,
            scenario_id=scenario_id,
            rating=data.rating,
            comment=data.comment,
        )
        return _to_review_response(review, display_name)

    async def list_public_playthroughs(
        self,
        scenario_id: uuid.UUID,
        limit: int = 10,
        current_user_id: uuid.UUID | None = None,
    ) -> list[PublicPlaythroughSummary]:
        """Fetch list of active/completed public playthroughs for scenario."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()
        await self.access.ensure_can_open(scenario, current_user_id)

        results = await self.scenario_repo.list_public_playthroughs(scenario_id, limit)
        summaries: list[PublicPlaythroughSummary] = []
        for pt, player_name in results:
            char_name = None
            if isinstance(pt.state, dict) and "character" in pt.state:
                char_data = pt.state["character"]
                if isinstance(char_data, dict):
                    char_name = char_data.get("name")
            summaries.append(
                PublicPlaythroughSummary(
                    playthrough_id=pt.playthrough_id,
                    player_name=player_name,
                    character_name=char_name,
                    turn_count=pt.turn_count,
                    status=pt.status,
                    updated_at=pt.updated_at,
                )
            )
        return summaries

    async def update_scenario(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ScenarioUpdate,
    ) -> ScenarioResponse:
        """Update scenario fields and selectively increment story version."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()

        is_draft = scenario.status == "draft"
        self._ensure_creator_access(scenario, user_id, hide_as_404=is_draft)

        ensure_not_publishing(scenario)
        ensure_not_stale(scenario, data.expected_content_edited_at)

        should_bump_version = False
        update_dict = data.model_dump(
            exclude_unset=True, exclude={"expected_content_edited_at"}
        )
        apply_rendered_documents(update_dict)
        _apply_mode_switch(scenario, update_dict)
        next_mode = str(update_dict.get("mode", scenario.mode))
        next_strategy_document = update_dict.get(
            "strategy_document", scenario.strategy_document
        )
        _validate_strategy_document_for_mode(next_mode, next_strategy_document)
        if "state_schema" in update_dict:
            validate_display_hints(
                update_dict["state_schema"],
                scenario.enabled_tools,
                scenario.state_schema,
            )
            validate_schema_fields(
                update_dict["state_schema"],
                scenario.enabled_tools,
                scenario.state_schema,
            )
            validate_reserved_roots(update_dict["state_schema"], scenario.enabled_tools)

        for field, value in update_dict.items():
            if field in STORY_SCHEMA_FIELDS and getattr(scenario, field) != value:
                should_bump_version = True
            setattr(scenario, field, value)

        if should_bump_version:
            scenario.current_version += 1

        updated_scenario = await self.scenario_repo.update(scenario)
        return ScenarioResponse.model_validate(updated_scenario)

    async def delete_scenario(self, scenario_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Hard delete an unpublished scenario with 0 playthroughs, else archive.

        A scenario that has ever been published is always archived, never
        hard-deleted, so players' links and history stay intact.
        """
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()

        is_draft = scenario.status == "draft"
        self._ensure_creator_access(scenario, user_id, hide_as_404=is_draft)

        playthrough_count = await self.scenario_repo.count_playthroughs(scenario_id)
        was_ever_published = scenario.published_at is not None
        if playthrough_count == 0 and not was_ever_published:
            await _purge_scenario_memory_best_effort(scenario_id)
            await self.scenario_repo.delete(scenario)
        else:
            scenario.status = "archived"
            await self.scenario_repo.update(scenario)

    async def list_scenarios(
        self,
        current_user_id: uuid.UUID | None = None,
        creator_id: uuid.UUID | None = None,
        mine: bool = False,
        saved: bool = False,
        played: bool = False,
        genre_tags: list[str] | None = None,
        complexity_tier: str | None = None,
        player_count_support: str | None = None,
        mode: str | None = None,
        playtime_bucket: str | None = None,
        query: str | None = None,
        include_mature: bool = False,
        sort_by: str = "created_at",
        limit: int = 20,
        offset: int = 0,
    ) -> ScenarioListResponse:
        """List published scenarios for discovery or creator's own scenarios."""
        if (mine or saved or played) and current_user_id is None:
            raise ScenarioAccessDeniedError("Must be logged in to view my scenarios")

        filters = ScenarioListFilters(
            creator_id=current_user_id if mine else creator_id,
            published_only=not mine,
            include_archived=played,
            include_mature=include_mature or mine or settings.is_alpha_mode,
            genre_tags=genre_tags,
            complexity_tier=complexity_tier,
            player_count_support=player_count_support,
            mode=mode,
            playtime_bucket=playtime_bucket,
            query=query,
            saved_by_user_id=current_user_id if saved else None,
            played_by_user_id=current_user_id if played else None,
            sort_by=sort_by,
            only_scenario_id=_alpha_scenario_filter(),
            viewer_id=current_user_id,
            include_private_for_viewer=mine or saved or played,
        )
        items, total_count = await self.scenario_repo.list_scenarios(
            filters, limit=limit, offset=offset
        )
        summaries = await self._build_summaries(items, current_user_id)

        return ScenarioListResponse(
            items=summaries,
            next_cursor=_next_cursor(offset, limit, total_count),
            total_count=total_count,
        )

    async def list_my_scenarios(
        self,
        user_id: uuid.UUID,
        tab: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> MyScenarioListResponse:
        """List the creator's own scenarios for the Studio, newest edit first."""
        filters = ScenarioListFilters(
            creator_id=user_id,
            statuses=STUDIO_TAB_STATUSES.get(tab) if tab else None,
            query=query,
            include_mature=True,
            sort_by=STUDIO_LIST_SORT,
            only_scenario_id=_alpha_scenario_filter(),
            viewer_id=user_id,
            include_private_for_viewer=True,
        )
        items, total_count = await self.scenario_repo.list_scenarios(
            filters, limit=limit, offset=offset
        )
        counts_by_status = await self.scenario_repo.count_creator_scenarios_by_status(
            user_id
        )
        return MyScenarioListResponse(
            items=await self._build_my_summaries(items),
            next_cursor=_next_cursor(offset, limit, total_count),
            total_count=total_count,
            status_counts=_to_status_counts(counts_by_status),
        )

    async def _build_my_summaries(
        self, items: list[Scenario]
    ) -> list[MyScenarioSummary]:
        if not items:
            return []
        review_counts = await self.scenario_repo.get_review_counts(
            [item.scenario_id for item in items]
        )
        summaries = []
        for item in items:
            summary = MyScenarioSummary.model_validate(item)
            summary.review_count = review_counts.get(item.scenario_id, 0)
            summary.has_unpublished_changes = _has_unpublished_changes(item)
            summaries.append(summary)
        return summaries

    async def _build_summaries(
        self, items: list[Scenario], current_user_id: uuid.UUID | None
    ) -> list[ScenarioSummaryResponse]:
        if not items:
            return []
        creator_names = await self.scenario_repo.get_creator_display_names(
            list({item.creator_id for item in items})
        )
        bookmarked_ids: set[uuid.UUID] = set()
        if current_user_id is not None:
            bookmarked_ids = await self.scenario_repo.get_bookmarked_scenario_ids(
                current_user_id, [item.scenario_id for item in items]
            )
        summaries = []
        for item in items:
            summary = ScenarioSummaryResponse.model_validate(item)
            summary.creator_display_name = (
                creator_names.get(item.creator_id) or ANONYMOUS_CREATOR_NAME
            )
            summary.is_bookmarked = item.scenario_id in bookmarked_ids
            summaries.append(summary)
        return summaries

    async def duplicate_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> ScenarioResponse:
        """Deep-copy a scenario, its mood music, its cards and links, and its master-mode sub-resources
        (kept while Advanced mode is off) as a new draft owned by the caller. Only the source scenario's owner may
        duplicate it (same ownership rule as update_scenario/delete_scenario).

        Note: entity references inside condition_expression/
        invariant_expression/state_mutation JSON are creator-facing dot-paths
        (e.g. "the_warden.health"), not entity UUIDs, so those JSON blobs are
        copied verbatim with no ID remap. Only Fact.subject_entity_id/
        object_entity_id (real FK columns) need remapping to the copied
        entities' new IDs.
        """
        source = await self.scenario_repo.get_by_id(scenario_id)
        if not source or source.status == "archived":
            raise ScenarioNotFoundError()
        self._ensure_creator_access(source, user_id)

        new_scenario = await self.scenario_repo.create(
            _build_scenario_copy(source, user_id)
        )
        await self._copy_music(source.scenario_id, new_scenario.scenario_id)
        entity_id_map = await self._copy_cards_and_links(
            source.scenario_id, new_scenario.scenario_id
        )
        await self._duplicate_master_resources(
            source.scenario_id, new_scenario.scenario_id, entity_id_map
        )

        return ScenarioResponse.model_validate(new_scenario)

    async def _copy_cards_and_links(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> dict[uuid.UUID, uuid.UUID]:
        """Deep-copy entity types, entities (cards) and facts (links), which
        exist in both modes. Returns the old->new entity ID map."""
        await self._copy_entity_types(source_scenario_id, new_scenario_id)
        entity_id_map = await self._copy_entities(source_scenario_id, new_scenario_id)
        await self._copy_facts(source_scenario_id, new_scenario_id, entity_id_map)
        return entity_id_map

    async def _duplicate_master_resources(
        self,
        source_scenario_id: uuid.UUID,
        new_scenario_id: uuid.UUID,
        entity_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> None:
        """Deep-copy the master-mode-only sub-resources in topological order."""
        await self._copy_conditions(source_scenario_id, new_scenario_id)
        await self._copy_end_conditions(source_scenario_id, new_scenario_id)
        await self._copy_invariants(source_scenario_id, new_scenario_id)
        await self._copy_maps_and_pins(
            source_scenario_id, new_scenario_id, entity_id_map
        )
        await self._copy_minigames(source_scenario_id, new_scenario_id)
        await self._copy_rule_checks(source_scenario_id, new_scenario_id)
        await self._copy_sheet_rules(source_scenario_id, new_scenario_id)

    async def _copy_entity_types(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> None:
        """Deep-copy custom entity type templates for a scenario."""
        source_types = await self.entity_type_repo.list_by_scenario(source_scenario_id)
        copies = [
            _build_entity_type_copy(entity_type, new_scenario_id)
            for entity_type in source_types
        ]
        await self.entity_type_repo.create_all(copies)

    async def _copy_entities(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> dict[uuid.UUID, uuid.UUID]:
        """Deep-copy every entity for a scenario. Returns old->new entity ID map."""
        source_entities = await self.entity_repo.list_by_scenario(source_scenario_id)
        copies = [
            _build_entity_copy(entity, new_scenario_id) for entity in source_entities
        ]
        id_map = {
            entity.entity_id: copy.entity_id
            for entity, copy in zip(source_entities, copies, strict=True)
        }
        await self.entity_repo.create_all(copies)
        return id_map

    async def _copy_facts(
        self,
        source_scenario_id: uuid.UUID,
        new_scenario_id: uuid.UUID,
        entity_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> None:
        """Deep-copy facts, remapping entity FKs immediately and superseded-
        fact FKs in a second pass once every fact's new ID is known."""
        source_facts = await self.fact_repo.list_by_scenario(source_scenario_id)
        new_facts = [
            _build_fact_copy(fact, new_scenario_id, entity_id_map)
            for fact in source_facts
        ]
        fact_id_map = {
            fact.fact_id: copy.fact_id
            for fact, copy in zip(source_facts, new_facts, strict=True)
        }
        await self.fact_repo.create_all(new_facts)
        await self._relink_superseded_facts(source_facts, new_facts, fact_id_map)

    async def _relink_superseded_facts(
        self,
        source_facts: list[Fact],
        new_facts: list[Fact],
        fact_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> None:
        """Point each copied fact's superseded_fact_id at its copied sibling."""
        for source_fact, new_fact in zip(source_facts, new_facts, strict=True):
            if source_fact.superseded_fact_id is None:
                continue
            new_fact.superseded_fact_id = fact_id_map.get(
                source_fact.superseded_fact_id
            )
            await self.fact_repo.update(new_fact)

    async def _copy_conditions(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> None:
        """Deep-copy active conditions verbatim (no entity-ID remap needed)."""
        source_conditions = await self.condition_repo.list_by_scenario(
            source_scenario_id
        )
        copies = [
            _build_condition_copy(condition, new_scenario_id)
            for condition in source_conditions
        ]
        await self.condition_repo.create_all(copies)

    async def _copy_end_conditions(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> None:
        """Deep-copy end conditions verbatim, preserving priority order."""
        source_end_conditions = await self.end_condition_repo.list_by_scenario(
            source_scenario_id
        )
        copies = [
            _build_end_condition_copy(end_condition, new_scenario_id)
            for end_condition in source_end_conditions
        ]
        await self.end_condition_repo.create_all(copies)

    async def _copy_invariants(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> None:
        """Deep-copy rule invariants verbatim (no entity-ID remap needed)."""
        source_invariants = await self.invariant_repo.list_by_scenario(
            source_scenario_id
        )
        copies = [
            _build_invariant_copy(invariant, new_scenario_id)
            for invariant in source_invariants
        ]
        await self.invariant_repo.create_all(copies)

    async def _copy_maps_and_pins(
        self,
        source_scenario_id: uuid.UUID,
        new_scenario_id: uuid.UUID,
        entity_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> None:
        """Deep-copy maps, pins, and map connections for a scenario."""
        map_id_map = await self._copy_maps(source_scenario_id, new_scenario_id)
        await self._copy_pins(
            source_scenario_id, new_scenario_id, map_id_map, entity_id_map
        )
        await self._copy_connections(source_scenario_id, new_scenario_id, entity_id_map)

    async def _copy_maps(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> dict[uuid.UUID, uuid.UUID]:
        """Deep-copy scenario maps. Returns old->new map ID map."""
        source_maps = await self.map_repo.list_maps_by_scenario(source_scenario_id)
        map_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for scenario_map in source_maps:
            copy = _build_map_copy(scenario_map, new_scenario_id)
            map_id_map[scenario_map.map_id] = copy.map_id
            await self.map_repo.create_map(copy)
        return map_id_map

    async def _copy_pins(
        self,
        source_scenario_id: uuid.UUID,
        new_scenario_id: uuid.UUID,
        map_id_map: dict[uuid.UUID, uuid.UUID],
        entity_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> None:
        """Deep-copy map pins, remapping map_id and entity_id."""
        source_pins = await self.map_repo.list_pins_by_scenario(source_scenario_id)
        for pin in source_pins:
            new_map_id = map_id_map.get(pin.map_id)
            new_entity_id = entity_id_map.get(pin.entity_id)
            if not new_map_id or not new_entity_id:
                continue
            copy = _build_pin_copy(pin, new_scenario_id, new_map_id, new_entity_id)
            await self.map_repo.create_pin(copy)

    async def _copy_connections(
        self,
        source_scenario_id: uuid.UUID,
        new_scenario_id: uuid.UUID,
        entity_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> None:
        """Deep-copy map connections, remapping and sorting entity IDs."""
        source_connections = await self.map_repo.list_connections_by_scenario(
            source_scenario_id
        )
        for conn in source_connections:
            new_a = entity_id_map.get(conn.entity_id_a)
            new_b = entity_id_map.get(conn.entity_id_b)
            if not new_a or not new_b:
                continue
            copy = _build_connection_copy(conn, new_scenario_id, new_a, new_b)
            await self.map_repo.create_connection(copy)

    async def _copy_minigames(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> None:
        """Deep-copy minigames for a scenario."""
        source_minigames = await self.minigame_repo.list_by_scenario(source_scenario_id)
        for minigame in source_minigames:
            copy = _build_minigame_copy(minigame, new_scenario_id)
            await self.minigame_repo.create(copy)

    async def _copy_rule_checks(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> None:
        """Deep-copy rule checks, including inert ones, preserving priority."""
        source_checks = await self.rule_check_repo.list_by_scenario(source_scenario_id)
        copies = [_build_rule_check_copy(c, new_scenario_id) for c in source_checks]
        await self.rule_check_repo.create_all(copies)

    async def _copy_sheet_rules(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> None:
        """Deep-copy sheet rules, including inert ones, preserving order."""
        source_rules = await self.sheet_rule_repo.list_by_scenario(source_scenario_id)
        copies = [_build_sheet_rule_copy(r, new_scenario_id) for r in source_rules]
        await self.sheet_rule_repo.create_all(copies)

    async def _copy_music(
        self, source_scenario_id: uuid.UUID, new_scenario_id: uuid.UUID
    ) -> None:
        source_tracks = await self.music_repo.get_by_scenario(source_scenario_id)
        copies = [_build_music_copy(track, new_scenario_id) for track in source_tracks]
        await self.music_repo.create_all(copies)

    def _ensure_creator_access(
        self,
        scenario: Scenario,
        user_id: uuid.UUID | None,
        hide_as_404: bool = False,
    ) -> None:
        """Verify user is the scenario creator."""
        if user_id is None or scenario.creator_id != user_id:
            if hide_as_404:
                raise ScenarioNotFoundError()
            raise ScenarioAccessDeniedError()


def _build_scenario_copy(source: Scenario, user_id: uuid.UUID) -> Scenario:
    """Build the new draft Scenario row for a duplicate, forcing status=draft
    and resetting publish/discovery-derived fields."""
    return Scenario(
        creator_id=user_id,
        title=f"{source.title} (Copy)",
        logline=source.logline,
        mode=source.mode,
        world_data=source.world_data,
        strategy_document=copy.deepcopy(source.strategy_document),
        strategy_data=copy.deepcopy(source.strategy_data),
        status="draft",
        visibility=source.visibility,
        genre_tags=list(source.genre_tags),
        complexity_tier=source.complexity_tier,
        player_count_support=source.player_count_support,
        estimated_playtime=source.estimated_playtime,
        cover_image_url=source.cover_image_url,
        content_tag=source.content_tag,
        content_tags=list(source.content_tags),
        narrator_persona=source.narrator_persona,
        narrator_persona_document=source.narrator_persona_document,
        mood_tags=list(source.mood_tags),
        player_mode=source.player_mode,
        setup_schema=source.setup_schema,
        state_schema=source.state_schema,
        end_conditions=source.end_conditions,
        checkpoints=source.checkpoints,
        rules=source.rules,
        opening_scene=source.opening_scene,
        narration_font=source.narration_font,
        narrator_voice_name=source.narrator_voice_name,
        action_chips=list(source.action_chips),
        setup_archetypes=source.setup_archetypes,
        enabled_tools=list(source.enabled_tools),
        current_version=1,
    )


def _build_entity_copy(entity: Entity, new_scenario_id: uuid.UUID) -> Entity:
    """Build a copied Entity row with a new ID under new_scenario_id."""
    return Entity(
        entity_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        entity_type=entity.entity_type,
        canonical_name=entity.canonical_name,
        aliases=list(entity.aliases),
        description=entity.description,
        lore_document=entity.lore_document,
        obtainable=entity.obtainable,
        attributes_schema=entity.attributes_schema,
        narrator_instruction=entity.narrator_instruction,
        is_player=entity.is_player,
    )


def _build_fact_copy(
    fact: Fact,
    new_scenario_id: uuid.UUID,
    entity_id_map: dict[uuid.UUID, uuid.UUID],
) -> Fact:
    """Build a copied Fact row, remapping subject/object entity FKs to their
    copied entities. superseded_fact_id is relinked by the caller once every
    fact in the batch has a new ID."""
    return Fact(
        fact_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        subject_entity_id=entity_id_map[fact.subject_entity_id],
        predicate=fact.predicate,
        object_entity_id=(
            entity_id_map.get(fact.object_entity_id) if fact.object_entity_id else None
        ),
        object_literal=fact.object_literal,
        valid_from=fact.valid_from,
        when_active=fact.when_active,
        hidden=fact.hidden,
        metadata_=fact.metadata_,
    )


def _build_condition_copy(
    condition: ScenarioCondition, new_scenario_id: uuid.UUID
) -> ScenarioCondition:
    """Build a copied ScenarioCondition row (expression fields are dot-path
    strings, not entity IDs, so they're copied verbatim).

    created_at is preserved because TRS evaluates conditions in that order.
    """
    return ScenarioCondition(
        condition_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        label=condition.label,
        condition_expression=condition.condition_expression,
        condition_version=condition.condition_version,
        narrator_instruction=condition.narrator_instruction,
        metadata_=condition.metadata_,
        state_mutation=condition.state_mutation,
        state_mutations=list(condition.state_mutations),
        is_one_shot=condition.is_one_shot,
        sensory_cue=condition.sensory_cue,
        cut_ambient=condition.cut_ambient,
        silence_duration_ms=condition.silence_duration_ms,
        created_at=condition.created_at,
    )


def _build_end_condition_copy(
    end_condition: EndCondition, new_scenario_id: uuid.UUID
) -> EndCondition:
    """Build a copied EndCondition row, preserving its priority."""
    return EndCondition(
        end_condition_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        condition_expression=end_condition.condition_expression,
        outcome_tag=end_condition.outcome_tag,
        outcome_title=end_condition.outcome_title,
        outcome_text=end_condition.outcome_text,
        is_secret=end_condition.is_secret,
        priority=end_condition.priority,
        metadata_=end_condition.metadata_,
    )


def _build_invariant_copy(
    invariant: RuleInvariant, new_scenario_id: uuid.UUID
) -> RuleInvariant:
    """Build a copied RuleInvariant row (expression fields are dot-path
    strings, not entity IDs, so they're copied verbatim)."""
    return RuleInvariant(
        invariant_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        label=invariant.label,
        invariant_expression=invariant.invariant_expression,
        applies_to=invariant.applies_to,
        narrator_text=invariant.narrator_text,
        metadata_=invariant.metadata_,
    )


def _build_entity_type_copy(
    entity_type: ScenarioEntityType, new_scenario_id: uuid.UUID
) -> ScenarioEntityType:
    """Build a copied ScenarioEntityType row under new_scenario_id."""
    return ScenarioEntityType(
        scenario_entity_type_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        type_key=entity_type.type_key,
        display_label=entity_type.display_label,
        attributes_schema=dict(entity_type.attributes_schema),
    )


def _build_music_copy(
    track: ScenarioMusic, new_scenario_id: uuid.UUID
) -> ScenarioMusic:
    return ScenarioMusic(
        scenario_music_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        mood=track.mood,
        source=track.source,
        track_url=track.track_url,
        generation_prompt=track.generation_prompt,
        key=track.key,
        bpm=track.bpm,
        duration_seconds=track.duration_seconds,
    )


def _build_map_copy(
    scenario_map: ScenarioMap, new_scenario_id: uuid.UUID
) -> ScenarioMap:
    """Build a copied ScenarioMap row under new_scenario_id."""
    return ScenarioMap(
        map_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        name=scenario_map.name,
        image_url=scenario_map.image_url,
        display_order=scenario_map.display_order,
    )


def _build_pin_copy(
    pin: MapPin,
    new_scenario_id: uuid.UUID,
    new_map_id: uuid.UUID,
    new_entity_id: uuid.UUID,
) -> MapPin:
    """Build a copied MapPin row with remapped map and entity FKs."""
    return MapPin(
        pin_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        map_id=new_map_id,
        entity_id=new_entity_id,
        x=pin.x,
        y=pin.y,
        is_start_location=pin.is_start_location,
    )


def _build_connection_copy(
    conn: MapConnection,
    new_scenario_id: uuid.UUID,
    new_a: uuid.UUID,
    new_b: uuid.UUID,
) -> MapConnection:
    """Build a copied MapConnection row with sorted remapped entity FKs."""
    sorted_a, sorted_b = min(new_a, new_b), max(new_a, new_b)
    return MapConnection(
        connection_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        entity_id_a=sorted_a,
        entity_id_b=sorted_b,
        label=conn.label,
    )


def _build_sheet_rule_copy(
    rule: ScenarioSheetRule, new_scenario_id: uuid.UUID
) -> ScenarioSheetRule:
    return ScenarioSheetRule(
        rule_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        key=rule.key,
        number=rule.number,
        text=rule.text,
        corrupted_text=rule.corrupted_text,
        initial_status=rule.initial_status,
        source_style=rule.source_style,
        is_ai_flaggable=rule.is_ai_flaggable,
        display_order=rule.display_order,
    )


def _build_rule_check_copy(
    check: ScenarioRuleCheck, new_scenario_id: uuid.UUID
) -> ScenarioRuleCheck:
    return ScenarioRuleCheck(
        check_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        label=check.label,
        kind=check.kind,
        trigger_condition_expression=check.trigger_condition_expression,
        priority=check.priority,
        result_path=check.result_path,
        params=check.params,
        narrator_instruction_template=check.narrator_instruction_template,
    )


def _build_minigame_copy(
    minigame: ScenarioMinigame, new_scenario_id: uuid.UUID
) -> ScenarioMinigame:
    """Build a copied ScenarioMinigame row under new_scenario_id."""
    return ScenarioMinigame(
        minigame_id=uuid.uuid4(),
        scenario_id=new_scenario_id,
        label=minigame.label,
        minigame_type=minigame.minigame_type,
        trigger_condition_expression=minigame.trigger_condition_expression,
        priority=minigame.priority,
        outcome_mode=minigame.outcome_mode,
        win_mutation=minigame.win_mutation,
        lose_mutation=minigame.lose_mutation,
        win_mutations=list(minigame.win_mutations),
        lose_mutations=list(minigame.lose_mutations),
        tiered_outcomes=list(minigame.tiered_outcomes),
        timeout_mutation=minigame.timeout_mutation,
        timeout_mutations=list(minigame.timeout_mutations),
        narrator_instruction_template=minigame.narrator_instruction_template,
        dodge_config=minigame.dodge_config,
        lockpick_config=minigame.lockpick_config,
        composure_config=minigame.composure_config,
    )
