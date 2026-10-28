"""Aggregation queries behind the creator stats screens."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.db.models.bookmark import Bookmark
from app.db.models.entity import Entity
from app.db.models.map_pin import MapPin
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.review import ScenarioReview
from app.db.models.scenario import Scenario
from app.db.models.scenario_map import ScenarioMap
from app.db.models.share import PlaythroughShare
from app.db.models.user import User
from sqlalchemy import (
    ColumnElement,
    Float,
    Label,
    RowMapping,
    Subquery,
    case,
    cast,
    func,
    literal,
    or_,
    select,
    true,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

ACTIVE_STATUS = "active"
COMPLETED_STATUS = "completed"
ABANDONED_STATUS = "abandoned"
WIN_TAG = "win"
LOSE_TAG = "lose"
JOINED_ROLE = "joined"
UTC_ZONE = "UTC"
REACHED_LABEL_PREFIX = "reached_"
PUBLISHED_STATUS = "published"
MEDIAN_PERCENTILE = 0.5
DISCOVERED_LOCATIONS_KEY = "discovered_location_ids"
JSON_ARRAY_TYPE = "array"


@dataclass(frozen=True)
class PlaythroughTotalsRow:
    scenario_id: uuid.UUID
    plays: int
    active_count: int
    ended_count: int
    abandoned_count: int
    win_count: int
    lose_count: int
    turn_total: int
    multiplayer_count: int
    distinct_players: int
    reached_turn_counts: tuple[int, ...]


@dataclass(frozen=True)
class LatestReviewRow:
    scenario_id: uuid.UUID
    scenario_title: str
    author_display_name: str
    rating: int
    comment: str | None
    created_at: datetime


@dataclass(frozen=True)
class VersionTotalsRow:
    scenario_version: int
    plays: int
    ended_count: int
    win_count: int
    turn_total: int


@dataclass(frozen=True)
class PeerFilter:
    exclude_scenario_id: uuid.UUID
    mode: str
    genre_tags: list[str] | None


@dataclass(frozen=True)
class PeerMediansRow:
    peer_count: int
    completion_rate: float | None
    average_turns: float | None
    win_rate: float | None
    average_rating: float | None
    win_rate_peer_count: int
    rating_peer_count: int


@dataclass(frozen=True)
class MapPinRow:
    map_id: uuid.UUID
    map_name: str
    image_url: str | None
    entity_id: uuid.UUID
    entity_name: str
    x: float
    y: float


def window_filters(
    column: InstrumentedAttribute[datetime], start: datetime | None, end: datetime
) -> list[ColumnElement[bool]]:
    filters = [column < end]
    if start is not None:
        filters.append(column >= start)
    return filters


def ended_condition() -> ColumnElement[bool]:
    return or_(
        Playthrough.status == COMPLETED_STATUS,
        Playthrough.ended_outcome_tag.is_not(None),
    )


def _playthrough_filters(
    scenario_ids: list[uuid.UUID], start: datetime | None, end: datetime
) -> list[ColumnElement[bool]]:
    return [
        Playthrough.scenario_id.in_(scenario_ids),
        Playthrough.is_playtest.is_(False),
        *window_filters(Playthrough.created_at, start, end),
    ]


def _reached_columns(turn_thresholds: list[int]) -> list[Label[int]]:
    return [
        func.count()
        .filter(or_(Playthrough.turn_count >= threshold, ended_condition()))
        .label(f"{REACHED_LABEL_PREFIX}{i}")
        for i, threshold in enumerate(turn_thresholds)
    ]


def _status_columns() -> list[Label[int]]:
    return [
        func.count().label("plays"),
        func.count().filter(Playthrough.status == ACTIVE_STATUS).label("active_count"),
        func.count().filter(ended_condition()).label("ended_count"),
        func.count()
        .filter(Playthrough.status == ABANDONED_STATUS)
        .label("abandoned_count"),
        func.count()
        .filter(Playthrough.ended_outcome_tag == WIN_TAG)
        .label("win_count"),
        func.count()
        .filter(Playthrough.ended_outcome_tag == LOSE_TAG)
        .label("lose_count"),
        func.coalesce(func.sum(Playthrough.turn_count), 0).label("turn_total"),
        func.count(func.distinct(Playthrough.created_by)).label("distinct_players"),
    ]


def _totals_row(mapping: RowMapping, threshold_count: int) -> PlaythroughTotalsRow:
    return PlaythroughTotalsRow(
        scenario_id=mapping["scenario_id"],
        plays=mapping["plays"],
        active_count=mapping["active_count"],
        ended_count=mapping["ended_count"],
        abandoned_count=mapping["abandoned_count"],
        win_count=mapping["win_count"],
        lose_count=mapping["lose_count"],
        turn_total=int(mapping["turn_total"]),
        multiplayer_count=mapping["multiplayer_count"],
        distinct_players=mapping["distinct_players"],
        reached_turn_counts=tuple(
            mapping[f"{REACHED_LABEL_PREFIX}{i}"] for i in range(threshold_count)
        ),
    )


def _median(column: ColumnElement[float]) -> ColumnElement[float]:
    return func.percentile_cont(MEDIAN_PERCENTILE).within_group(column)


def _optional_float(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _peer_filters(peer_filter: PeerFilter) -> list[ColumnElement[bool]]:
    filters = [
        Scenario.status == PUBLISHED_STATUS,
        Scenario.mode == peer_filter.mode,
        Scenario.scenario_id != peer_filter.exclude_scenario_id,
    ]
    if peer_filter.genre_tags is not None:
        filters.append(Scenario.genre_tags.overlap(peer_filter.genre_tags))
    return filters


def _peer_metrics_subquery(
    peer_filter: PeerFilter,
    start: datetime | None,
    end: datetime,
    min_playthroughs: int,
) -> Subquery:
    ended = func.count().filter(ended_condition())
    wins = func.count().filter(Playthrough.ended_outcome_tag == WIN_TAG)
    return (
        select(
            Playthrough.scenario_id,
            (cast(ended, Float) / func.count()).label("completion_rate"),
            cast(func.avg(Playthrough.turn_count), Float).label("average_turns"),
            (cast(wins, Float) / func.nullif(ended, 0)).label("win_rate"),
        )
        .join(Scenario, Scenario.scenario_id == Playthrough.scenario_id)
        .where(
            *_peer_filters(peer_filter),
            Playthrough.is_playtest.is_(False),
            *window_filters(Playthrough.created_at, start, end),
        )
        .group_by(Playthrough.scenario_id)
        .having(func.count() >= min_playthroughs)
        .subquery()
    )


def _rating_averages_subquery(start: datetime | None, end: datetime) -> Subquery:
    return (
        select(
            ScenarioReview.scenario_id,
            cast(func.avg(ScenarioReview.rating), Float).label("average_rating"),
        )
        .where(*window_filters(ScenarioReview.created_at, start, end))
        .group_by(ScenarioReview.scenario_id)
        .subquery()
    )


class CreatorStatsRepo:
    """Read-only aggregation queries for creator stats."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_playthrough_totals(
        self,
        scenario_ids: list[uuid.UUID],
        start: datetime | None,
        end: datetime,
        turn_thresholds: list[int],
    ) -> list[PlaythroughTotalsRow]:
        joined = (
            select(Participant.playthrough_id)
            .where(Participant.role == JOINED_ROLE)
            .distinct()
            .subquery()
        )
        stmt = (
            select(
                Playthrough.scenario_id,
                *_status_columns(),
                func.count(joined.c.playthrough_id).label("multiplayer_count"),
                *_reached_columns(turn_thresholds),
            )
            .outerjoin(joined, joined.c.playthrough_id == Playthrough.playthrough_id)
            .where(*_playthrough_filters(scenario_ids, start, end))
            .group_by(Playthrough.scenario_id)
        )
        result = await self.session.execute(stmt)
        return [_totals_row(row._mapping, len(turn_thresholds)) for row in result.all()]

    async def count_distinct_players(
        self, scenario_ids: list[uuid.UUID], start: datetime | None, end: datetime
    ) -> int:
        stmt = select(func.count(func.distinct(Playthrough.created_by))).where(
            *_playthrough_filters(scenario_ids, start, end)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_repeat_players(
        self,
        scenario_id: uuid.UUID,
        start: datetime | None,
        end: datetime,
        min_playthroughs: int,
    ) -> int:
        repeaters = (
            select(Playthrough.created_by)
            .where(*_playthrough_filters([scenario_id], start, end))
            .group_by(Playthrough.created_by)
            .having(func.count() >= min_playthroughs)
            .subquery()
        )
        stmt = select(func.count()).select_from(repeaters)
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_play_series(
        self,
        scenario_ids: list[uuid.UUID],
        start: datetime | None,
        end: datetime,
        bucket: str,
    ) -> list[tuple[datetime, int]]:
        # NOTE: literal_execute inlines the bucket and zone so the SELECT and
        # GROUP BY expressions are textually identical; two bind params would
        # make Postgres reject the grouping.
        bucket_start = func.date_trunc(
            literal(bucket, literal_execute=True),
            func.timezone(
                literal(UTC_ZONE, literal_execute=True), Playthrough.created_at
            ),
        ).label("bucket_start")
        stmt = (
            select(bucket_start, func.count())
            .where(*_playthrough_filters(scenario_ids, start, end))
            .group_by(bucket_start)
            .order_by(bucket_start)
        )
        result = await self.session.execute(stmt)
        return [(row[0], int(row[1])) for row in result.all()]

    async def get_turn_count_frequencies(
        self, scenario_id: uuid.UUID, start: datetime | None, end: datetime
    ) -> list[tuple[int, int]]:
        stmt = (
            select(Playthrough.turn_count, func.count())
            .where(*_playthrough_filters([scenario_id], start, end))
            .group_by(Playthrough.turn_count)
        )
        result = await self.session.execute(stmt)
        return [(int(row[0]), int(row[1])) for row in result.all()]

    async def get_rating_counts(
        self, scenario_ids: list[uuid.UUID], start: datetime | None, end: datetime
    ) -> list[tuple[uuid.UUID, int, int]]:
        stmt = (
            select(ScenarioReview.scenario_id, ScenarioReview.rating, func.count())
            .where(
                ScenarioReview.scenario_id.in_(scenario_ids),
                *window_filters(ScenarioReview.created_at, start, end),
            )
            .group_by(ScenarioReview.scenario_id, ScenarioReview.rating)
        )
        result = await self.session.execute(stmt)
        return [(row[0], int(row[1]), int(row[2])) for row in result.all()]

    async def list_latest_reviews(
        self,
        scenario_ids: list[uuid.UUID],
        start: datetime | None,
        end: datetime,
        limit: int,
    ) -> list[LatestReviewRow]:
        stmt = (
            select(
                ScenarioReview.scenario_id,
                Scenario.title,
                User.display_name,
                ScenarioReview.rating,
                ScenarioReview.comment,
                ScenarioReview.created_at,
            )
            .join(Scenario, Scenario.scenario_id == ScenarioReview.scenario_id)
            .join(User, User.user_id == ScenarioReview.user_id)
            .where(
                ScenarioReview.scenario_id.in_(scenario_ids),
                *window_filters(ScenarioReview.created_at, start, end),
            )
            .order_by(ScenarioReview.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [LatestReviewRow(*row) for row in result.all()]

    async def count_bookmarks(
        self, scenario_id: uuid.UUID, start: datetime | None, end: datetime
    ) -> int:
        stmt = select(func.count()).where(
            Bookmark.scenario_id == scenario_id,
            *window_filters(Bookmark.created_at, start, end),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_share_counts(
        self, scenario_id: uuid.UUID, start: datetime | None, end: datetime
    ) -> dict[str, int]:
        stmt = (
            select(PlaythroughShare.mode, func.count())
            .join(
                Playthrough,
                Playthrough.playthrough_id == PlaythroughShare.playthrough_id,
            )
            .where(
                Playthrough.scenario_id == scenario_id,
                Playthrough.is_playtest.is_(False),
                *window_filters(PlaythroughShare.created_at, start, end),
            )
            .group_by(PlaythroughShare.mode)
        )
        result = await self.session.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}

    async def list_stats_scenarios(
        self, creator_id: uuid.UUID, statuses: list[str]
    ) -> list[Scenario]:
        stmt = (
            select(Scenario)
            .where(Scenario.creator_id == creator_id, Scenario.status.in_(statuses))
            .order_by(Scenario.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_version_totals(
        self, scenario_id: uuid.UUID, start: datetime | None, end: datetime
    ) -> list[VersionTotalsRow]:
        stmt = (
            select(
                Playthrough.scenario_version,
                func.count(),
                func.count().filter(ended_condition()),
                func.count().filter(Playthrough.ended_outcome_tag == WIN_TAG),
                func.coalesce(func.sum(Playthrough.turn_count), 0),
            )
            .where(*_playthrough_filters([scenario_id], start, end))
            .group_by(Playthrough.scenario_version)
            .order_by(Playthrough.scenario_version.desc())
        )
        result = await self.session.execute(stmt)
        return [
            VersionTotalsRow(*(int(value) for value in row)) for row in result.all()
        ]

    async def get_end_condition_counts(
        self, scenario_id: uuid.UUID, start: datetime | None, end: datetime
    ) -> list[tuple[str, int]]:
        hit_count = func.count().label("hit_count")
        stmt = (
            select(Playthrough.ended_outcome_title, hit_count)
            .where(
                *_playthrough_filters([scenario_id], start, end),
                Playthrough.ended_outcome_title.is_not(None),
            )
            .group_by(Playthrough.ended_outcome_title)
            .order_by(hit_count.desc(), Playthrough.ended_outcome_title)
        )
        result = await self.session.execute(stmt)
        return [(str(row[0]), int(row[1])) for row in result.all()]

    async def get_peer_medians(
        self,
        peer_filter: PeerFilter,
        start: datetime | None,
        end: datetime,
        min_playthroughs: int,
    ) -> PeerMediansRow:
        # TRADE-OFF: the rating subquery averages every scenario in range, not
        # just peers; the outer join discards the rest. Fine at current scale.
        peers = _peer_metrics_subquery(peer_filter, start, end, min_playthroughs)
        ratings = _rating_averages_subquery(start, end)
        stmt = select(
            func.count(),
            _median(peers.c.completion_rate),
            _median(peers.c.average_turns),
            _median(peers.c.win_rate),
            _median(ratings.c.average_rating),
            func.count(peers.c.win_rate),
            func.count(ratings.c.average_rating),
        ).select_from(
            peers.outerjoin(ratings, ratings.c.scenario_id == peers.c.scenario_id)
        )
        row = (await self.session.execute(stmt)).one()
        return PeerMediansRow(
            peer_count=int(row[0]),
            completion_rate=_optional_float(row[1]),
            average_turns=_optional_float(row[2]),
            win_rate=_optional_float(row[3]),
            average_rating=_optional_float(row[4]),
            win_rate_peer_count=int(row[5]),
            rating_peer_count=int(row[6]),
        )

    async def list_map_pins(self, scenario_id: uuid.UUID) -> list[MapPinRow]:
        stmt = (
            select(
                ScenarioMap.map_id,
                ScenarioMap.name,
                ScenarioMap.image_url,
                MapPin.entity_id,
                Entity.canonical_name,
                MapPin.x,
                MapPin.y,
            )
            .join(MapPin, MapPin.map_id == ScenarioMap.map_id)
            .join(Entity, Entity.entity_id == MapPin.entity_id)
            .where(ScenarioMap.scenario_id == scenario_id)
            .order_by(
                ScenarioMap.display_order, ScenarioMap.name, Entity.canonical_name
            )
        )
        result = await self.session.execute(stmt)
        return [MapPinRow(*row) for row in result.all()]

    async def get_discovery_counts(
        self, scenario_id: uuid.UUID, start: datetime | None, end: datetime
    ) -> dict[str, int]:
        discovered = Playthrough.state[DISCOVERED_LOCATIONS_KEY]
        safe_array = case(
            (func.jsonb_typeof(discovered) == JSON_ARRAY_TYPE, discovered),
            else_=func.jsonb_build_array(),
        )
        elements = (
            func.jsonb_array_elements_text(safe_array).table_valued("value").lateral()
        )
        stmt = (
            select(
                elements.c.value, func.count(func.distinct(Playthrough.playthrough_id))
            )
            .select_from(Playthrough)
            .join(elements, true())
            .where(*_playthrough_filters([scenario_id], start, end))
            .group_by(elements.c.value)
        )
        result = await self.session.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}
