"""Bump Scenario.content_edited_at whenever an author edits scenario content.

updated_at cannot serve this purpose: plays, reviews and publish status changes
also bump it, which would flag every played scenario as having unpublished
changes.
"""

import uuid

from sqlalchemy import event, func, inspect, update
from sqlalchemy.orm import Session

from app.db.models.end_condition import EndCondition
from app.db.models.entity import Entity
from app.db.models.fact import Fact
from app.db.models.map_connection import MapConnection
from app.db.models.map_pin import MapPin
from app.db.models.rule_invariant import RuleInvariant
from app.db.models.scenario import Scenario
from app.db.models.scenario_condition import ScenarioCondition
from app.db.models.scenario_entity_type import ScenarioEntityType
from app.db.models.scenario_map import ScenarioMap
from app.db.models.scenario_minigame import ScenarioMinigame
from app.db.models.scenario_music import ScenarioMusic
from app.db.models.scenario_rule_check import ScenarioRuleCheck

AUTHORED_CHILD_MODELS: tuple[type, ...] = (
    EndCondition,
    Entity,
    Fact,
    MapConnection,
    MapPin,
    RuleInvariant,
    ScenarioCondition,
    ScenarioEntityType,
    ScenarioMap,
    ScenarioMinigame,
    ScenarioMusic,
    ScenarioRuleCheck,
)
NON_CONTENT_SCENARIO_COLUMNS = frozenset(
    {
        "status",
        "publish_error",
        "published_at",
        "published_content_edited_at",
        "content_edited_at",
        "updated_at",
        "play_count",
        "rating_avg",
        "guide_seen_features",
        "visibility",
    }
)


def _is_content_edit_to_scenario(scenario: Scenario) -> bool:
    changed_columns = {
        attribute.key
        for attribute in inspect(scenario).attrs
        if attribute.history.has_changes()
    }
    return bool(changed_columns - NON_CONTENT_SCENARIO_COLUMNS)


def _is_dirty_scenario_content_edit(session: Session, instance: object) -> bool:
    return (
        isinstance(instance, Scenario)
        and instance in session.dirty
        and _is_content_edit_to_scenario(instance)
    )


def _collect_edited_scenario_ids(session: Session) -> set[uuid.UUID]:
    edited_ids: set[uuid.UUID] = set()
    for instance in (*session.new, *session.dirty, *session.deleted):
        if isinstance(
            instance, AUTHORED_CHILD_MODELS
        ) or _is_dirty_scenario_content_edit(session, instance):
            edited_ids.add(instance.scenario_id)
    return edited_ids


@event.listens_for(Session, "before_flush")
def bump_content_edited_at(session: Session, *_: object) -> None:
    edited_ids = _collect_edited_scenario_ids(session)
    if not edited_ids:
        return
    session.execute(
        update(Scenario)
        .where(Scenario.scenario_id.in_(edited_ids))
        .values(content_edited_at=func.clock_timestamp())
        .execution_options(synchronize_session=False)
    )
