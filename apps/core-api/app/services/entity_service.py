"""Entity domain service handling business logic and scenario-ownership rules."""

import uuid
from datetime import datetime

from app.db.models.entity import Entity
from app.db.models.scenario import Scenario
from app.exceptions.entity_exceptions import EntityNotFoundError, EntityValidationError
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.models.entity import (
    ENTITY_TYPES,
    EntityCreate,
    EntityResponse,
    EntityTypeChangePreviewResponse,
    EntityUpdate,
)
from app.models.lore_document import LoreDocument
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.scenario_entity_type_repo import ScenarioEntityTypeRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.lore_render import render_lore_document
from app.services.scenario_edit_guard import ensure_not_publishing, ensure_not_stale


class EntityService:
    """Service handling entity authoring within a scenario."""

    def __init__(
        self,
        entity_repo: EntityRepo,
        scenario_repo: ScenarioRepo,
        fact_repo: FactRepo,
        entity_type_repo: ScenarioEntityTypeRepo,
    ) -> None:
        self.entity_repo = entity_repo
        self.scenario_repo = scenario_repo
        self.fact_repo = fact_repo
        self.entity_type_repo = entity_type_repo

    async def create_entity(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID, data: EntityCreate
    ) -> EntityResponse:
        """Create a new entity owned by the given scenario."""
        scenario = await self._ensure_editable_scenario(
            scenario_id, user_id, data.expected_content_edited_at
        )
        await self._ensure_valid_entity_type(scenario_id, data.entity_type)
        self._validate_player_entity_type(data.entity_type, data.is_player)
        if data.is_player:
            await self._handle_player_designation(scenario_id, None)

        entity = Entity(
            scenario_id=scenario_id,
            entity_type=data.entity_type,
            canonical_name=data.canonical_name,
            aliases=data.aliases,
            description=self._resolve_description(data),
            lore_document=self._dump_lore_document(data.lore_document),
            obtainable=data.obtainable,
            attributes_schema={
                key: field.model_dump() for key, field in data.attributes_schema.items()
            },
            narrator_instruction=data.narrator_instruction,
            is_player=data.is_player,
        )
        created = await self.entity_repo.create(entity)
        return await self._to_stamped_response(created, scenario)

    async def list_entities(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[EntityResponse]:
        """List all entities for a scenario, each with its related fact count."""
        await self._ensure_scenario_owner(scenario_id, user_id)
        entities = await self.entity_repo.list_by_scenario(scenario_id)
        fact_counts = await self.fact_repo.count_by_entity_for_scenario(scenario_id)
        return [
            EntityResponse.model_validate(e).model_copy(
                update={"fact_count": fact_counts.get(e.entity_id, 0)}
            )
            for e in entities
        ]

    async def get_entity(
        self, scenario_id: uuid.UUID, entity_id: uuid.UUID, user_id: uuid.UUID
    ) -> EntityResponse:
        """Fetch a single entity, scoped to its owning scenario."""
        await self._ensure_scenario_owner(scenario_id, user_id)
        entity = await self._get_scoped_entity(scenario_id, entity_id)
        fact_count = await self.fact_repo.count_referencing_entity(entity_id)
        return EntityResponse.model_validate(entity).model_copy(
            update={"fact_count": fact_count}
        )

    async def update_entity(
        self,
        scenario_id: uuid.UUID,
        entity_id: uuid.UUID,
        user_id: uuid.UUID,
        data: EntityUpdate,
    ) -> EntityResponse:
        """Update an entity's mutable fields, including its type."""
        scenario = await self._ensure_editable_scenario(
            scenario_id, user_id, data.expected_content_edited_at
        )
        entity = await self._get_scoped_entity(scenario_id, entity_id)

        # NOTE: model_dump() recursively dumps nested AttributeFieldSchema models to
        # plain dicts, matching the JSONB column shape — no special-casing needed.
        update_dict = data.model_dump(
            exclude_unset=True, exclude={"lore_document", "expected_content_edited_at"}
        )
        self._apply_lore_document_update(update_dict, data)
        await self._validate_entity_update(scenario_id, entity, update_dict)

        for field, value in update_dict.items():
            setattr(entity, field, value)

        updated = await self.entity_repo.update(entity)
        return await self._to_stamped_response(updated, scenario)

    async def _validate_entity_update(
        self, scenario_id: uuid.UUID, entity: Entity, update_dict: dict[str, object]
    ) -> None:
        next_type = update_dict.get("entity_type", entity.entity_type)
        next_is_player = update_dict.get("is_player", entity.is_player)
        if "entity_type" in update_dict:
            await self._ensure_valid_entity_type(
                scenario_id, str(update_dict["entity_type"])
            )
        self._validate_player_entity_type(str(next_type), bool(next_is_player))
        if update_dict.get("is_player") is True:
            await self._handle_player_designation(scenario_id, entity.entity_id)

    async def preview_type_change(
        self,
        scenario_id: uuid.UUID,
        entity_id: uuid.UUID,
        user_id: uuid.UUID,
        new_entity_type: str,
    ) -> EntityTypeChangePreviewResponse:
        """Compare an entity's current attributes against a prospective new
        type's template, without committing the change. Purely advisory: the
        entity's attributes_schema is never auto-migrated by a type change."""
        await self._ensure_scenario_owner(scenario_id, user_id)
        entity = await self._get_scoped_entity(scenario_id, entity_id)
        await self._ensure_valid_entity_type(scenario_id, new_entity_type)

        current_keys = set(entity.attributes_schema.keys())
        new_template = await self._get_type_template(scenario_id, new_entity_type)
        if not new_template:
            # NOTE: Built-in types (and empty custom templates) impose no schema
            # constraints, so nothing is flagged as "dropped".
            return EntityTypeChangePreviewResponse(retained_fields=sorted(current_keys))

        new_keys = set(new_template.keys())
        return EntityTypeChangePreviewResponse(
            dropped_fields=sorted(current_keys - new_keys),
            retained_fields=sorted(current_keys & new_keys),
            added_fields=sorted(new_keys - current_keys),
        )

    async def delete_entity(
        self,
        scenario_id: uuid.UUID,
        entity_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_content_edited_at: datetime | None = None,
    ) -> int:
        """Delete an entity and return how many facts (links) went with it."""
        await self._ensure_editable_scenario(
            scenario_id, user_id, expected_content_edited_at
        )
        entity = await self._get_scoped_entity(scenario_id, entity_id)
        removed_link_count = await self.fact_repo.count_referencing_entity(entity_id)
        await self.entity_repo.delete(entity)
        return removed_link_count

    def _resolve_description(self, data: EntityCreate) -> str | None:
        if data.lore_document is None:
            return data.description
        return render_lore_document(data.lore_document)

    def _dump_lore_document(
        self, lore_document: LoreDocument | None
    ) -> dict[str, object] | None:
        if lore_document is None:
            return None
        return lore_document.model_dump()

    def _apply_lore_document_update(
        self, update_dict: dict[str, object], data: EntityUpdate
    ) -> None:
        """The document is the single source: when it is sent, it overwrites
        any description sent alongside it."""
        if "lore_document" not in data.model_fields_set:
            return
        update_dict["lore_document"] = self._dump_lore_document(data.lore_document)
        if data.lore_document is not None:
            update_dict["description"] = render_lore_document(data.lore_document)

    async def _ensure_valid_entity_type(
        self, scenario_id: uuid.UUID, entity_type: str
    ) -> None:
        """Reject an entity_type that is neither built-in nor a defined
        custom type template for this scenario."""
        if entity_type in ENTITY_TYPES:
            return
        custom_type = await self.entity_type_repo.get_by_type_key(
            scenario_id, entity_type
        )
        if custom_type is None:
            raise EntityValidationError(
                f"Entity type '{entity_type}' is not defined for this scenario"
            )

    async def _get_type_template(
        self, scenario_id: uuid.UUID, entity_type: str
    ) -> dict[str, object]:
        """Fetch a type's attributes_schema template, empty for built-ins."""
        if entity_type in ENTITY_TYPES:
            return {}
        custom_type = await self.entity_type_repo.get_by_type_key(
            scenario_id, entity_type
        )
        return custom_type.attributes_schema if custom_type else {}

    async def _get_scoped_entity(
        self, scenario_id: uuid.UUID, entity_id: uuid.UUID
    ) -> Entity:
        """Fetch an entity, raising 404 if missing or owned by another scenario."""
        entity = await self.entity_repo.get_by_id(entity_id)
        if entity is None or entity.scenario_id != scenario_id:
            raise EntityNotFoundError()
        return entity

    async def _ensure_editable_scenario(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_content_edited_at: datetime | None = None,
    ) -> Scenario:
        scenario = await self._ensure_scenario_owner(scenario_id, user_id)
        ensure_not_publishing(scenario)
        ensure_not_stale(scenario, expected_content_edited_at)
        return scenario

    async def _to_stamped_response(
        self, entity: Entity, scenario: Scenario
    ) -> EntityResponse:
        """The write moved the story's edit stamp; hand the new one back so the
        client's next write can name it."""
        refreshed = await self.scenario_repo.refresh(scenario)
        return EntityResponse.model_validate(entity).model_copy(
            update={"scenario_content_edited_at": refreshed.content_edited_at}
        )

    async def _ensure_scenario_owner(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        """Verify the scenario exists and the requesting user is its creator."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if scenario is None or scenario.status == "archived":
            raise ScenarioNotFoundError()
        if scenario.creator_id != user_id:
            raise ScenarioAccessDeniedError()
        return scenario

    def _validate_player_entity_type(
        self, entity_type: str, is_player: bool | None
    ) -> None:
        """Reject designating a non-character entity as the player."""
        if is_player and entity_type != "character":
            raise EntityValidationError(
                "Only character entities can be designated as the player"
            )

    async def _handle_player_designation(
        self, scenario_id: uuid.UUID, current_entity_id: uuid.UUID | None
    ) -> None:
        """Ensure only one entity per scenario has is_player=True."""
        existing = await self.entity_repo.get_player_entity(scenario_id)
        if existing and existing.entity_id != current_entity_id:
            existing.is_player = False
            await self.entity_repo.update(existing)
