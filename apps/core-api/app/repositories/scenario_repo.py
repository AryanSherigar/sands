"""Scenario data repository for direct database operations."""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.db.models.bookmark import Bookmark
from app.db.models.playthrough import Playthrough
from app.db.models.review import ScenarioReview
from app.db.models.scenario import PUBLIC_VISIBILITY, Scenario
from app.db.models.scenario_access import ScenarioAccess
from app.db.models.user import User
from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

LIKE_ESCAPE_CHAR = "\\"
GENRE_TAG_SEPARATOR = " "
DRAFT_STATUSES = ("draft",)
PUBLISHED_TAB_STATUSES = ("published", "publishing", "publish_failed")
ARCHIVED_STATUSES = ("archived",)
REBUILDABLE_STATUSES = ("published", "publish_failed")


@dataclass(frozen=True)
class ScenarioListFilters:
    statuses: tuple[str, ...] | None = None
    creator_id: uuid.UUID | None = None
    published_only: bool = False
    include_archived: bool = False
    include_mature: bool = True
    genre_tags: list[str] | None = None
    complexity_tier: str | None = None
    player_count_support: str | None = None
    mode: str | None = None
    playtime_bucket: str | None = None
    query: str | None = None
    saved_by_user_id: uuid.UUID | None = None
    played_by_user_id: uuid.UUID | None = None
    sort_by: str = "created_at"
    only_scenario_id: uuid.UUID | None = None
    viewer_id: uuid.UUID | None = None
    include_private_for_viewer: bool = False


@dataclass(frozen=True)
class CreatorCard:
    display_name: str | None
    avatar_url: str | None
    bio: str | None


class ScenarioRepo:
    """Repository managing direct SQLAlchemy queries for Scenario entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, scenario: Scenario) -> Scenario:
        """Persist a new Scenario entity."""
        self.session.add(scenario)
        await self.session.flush()
        return scenario

    async def get_by_id(self, scenario_id: uuid.UUID) -> Scenario | None:
        """Retrieve a scenario by its primary key ID."""
        stmt = select(Scenario).where(Scenario.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_visibility(self, scenario_id: uuid.UUID) -> str | None:
        stmt = select(Scenario.visibility).where(Scenario.scenario_id == scenario_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_id_for_update(self, scenario_id: uuid.UUID) -> Scenario | None:
        """Retrieve a scenario by primary key with an exclusive row lock (FOR UPDATE)."""
        stmt = (
            select(Scenario)
            .where(Scenario.scenario_id == scenario_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update(self, scenario: Scenario) -> Scenario:
        """Flush changes to an existing scenario entity."""
        await self.session.flush()
        await self.session.refresh(scenario)
        return scenario

    async def refresh(self, scenario: Scenario) -> Scenario:
        """Reload database-maintained columns such as content_edited_at."""
        await self.session.refresh(scenario)
        return scenario

    async def delete(self, scenario: Scenario) -> None:
        """Permanently delete a scenario entity from DB."""
        await self.session.delete(scenario)
        await self.session.flush()

    async def list_published_for_memory_rebuild(self) -> list[Scenario]:
        """Scenarios that have been published at least once (a failed republish
        keeps its last published content), oldest first."""
        stmt = (
            select(Scenario)
            .where(
                Scenario.status.in_(REBUILDABLE_STATUSES),
                Scenario.published_at.is_not(None),
            )
            .order_by(Scenario.created_at, Scenario.scenario_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_playthroughs(self, scenario_id: uuid.UUID) -> int:
        """Count total playthroughs associated with a scenario ID."""
        stmt = (
            select(func.count())
            .select_from(Playthrough)
            .where(Playthrough.scenario_id == scenario_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def list_scenarios(
        self, filters: ScenarioListFilters, limit: int = 20, offset: int = 0
    ) -> tuple[list[Scenario], int]:
        """Fetch scenarios matching discovery or creator dashboard filters."""
        stmt = self._apply_filters(select(Scenario), filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar_one() or 0

        stmt = self._apply_sorting(stmt, filters.sort_by).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total_count

    def _apply_filters(self, stmt: select, filters: ScenarioListFilters) -> select:
        stmt = self._apply_scalar_filters(stmt, filters)
        if filters.genre_tags:
            stmt = stmt.where(Scenario.genre_tags.overlap(filters.genre_tags))
        if filters.query:
            stmt = stmt.where(self._build_text_match(filters.query))
        if filters.saved_by_user_id is not None:
            stmt = stmt.join(
                Bookmark, Bookmark.scenario_id == Scenario.scenario_id
            ).where(Bookmark.user_id == filters.saved_by_user_id)
        if filters.played_by_user_id is not None:
            stmt = (
                stmt.join(Playthrough, Playthrough.scenario_id == Scenario.scenario_id)
                .where(Playthrough.created_by == filters.played_by_user_id)
                .distinct()
            )
        return stmt

    def _apply_scalar_filters(
        self, stmt: select, filters: ScenarioListFilters
    ) -> select:
        stmt = self._apply_visibility(stmt, filters)
        if filters.only_scenario_id is not None:
            stmt = stmt.where(Scenario.scenario_id == filters.only_scenario_id)
        if filters.creator_id is not None:
            stmt = stmt.where(Scenario.creator_id == filters.creator_id)
        if filters.statuses is not None:
            stmt = stmt.where(Scenario.status.in_(filters.statuses))
        if filters.published_only:
            # NOTE: published_at (not status) is the discovery-visibility signal: a
            # re-publish attempt can transiently move status away from
            # 'published' without the scenario leaving the live feed.
            stmt = stmt.where(Scenario.published_at.is_not(None))
        if filters.published_only and not filters.include_archived:
            stmt = stmt.where(Scenario.status.not_in(ARCHIVED_STATUSES))
        if not filters.include_mature:
            stmt = stmt.where(Scenario.is_mature.is_(False))
        equality_filters = {
            Scenario.complexity_tier: filters.complexity_tier,
            Scenario.player_count_support: filters.player_count_support,
            Scenario.mode: filters.mode,
            Scenario.playtime_bucket: filters.playtime_bucket,
        }
        for column, value in equality_filters.items():
            if value is not None:
                stmt = stmt.where(column == value)
        return stmt

    def _apply_visibility(self, stmt: select, filters: ScenarioListFilters) -> select:
        """Private scenarios appear only in a viewer's own lists, never in discovery."""
        viewer = filters.viewer_id
        if not filters.include_private_for_viewer or viewer is None:
            return stmt.where(Scenario.visibility == PUBLIC_VISIBILITY)
        is_allowed = exists().where(
            ScenarioAccess.scenario_id == Scenario.scenario_id,
            ScenarioAccess.user_id == viewer,
        )
        return stmt.where(
            or_(
                Scenario.visibility == PUBLIC_VISIBILITY,
                Scenario.creator_id == viewer,
                is_allowed,
            )
        )

    def _build_text_match(self, query: str) -> ColumnElement[bool]:
        escaped = (
            query.replace(LIKE_ESCAPE_CHAR, LIKE_ESCAPE_CHAR * 2)
            .replace("%", f"{LIKE_ESCAPE_CHAR}%")
            .replace("_", f"{LIKE_ESCAPE_CHAR}_")
        )
        pattern = f"%{escaped}%"
        genre_text = func.array_to_string(Scenario.genre_tags, GENRE_TAG_SEPARATOR)
        return or_(
            Scenario.title.ilike(pattern, escape=LIKE_ESCAPE_CHAR),
            Scenario.logline.ilike(pattern, escape=LIKE_ESCAPE_CHAR),
            genre_text.ilike(pattern, escape=LIKE_ESCAPE_CHAR),
        )

    def _apply_sorting(self, stmt: select, sort_by: str) -> select:
        """Apply sort order to scenario list query."""
        if sort_by == "play_count":
            return stmt.order_by(Scenario.play_count.desc())
        if sort_by == "rating_avg":
            return stmt.order_by(Scenario.rating_avg.desc())
        if sort_by == "edited":
            # scenario_id breaks ties so offset paging never repeats or skips a row
            return stmt.order_by(
                Scenario.content_edited_at.desc(), Scenario.scenario_id.desc()
            )
        return stmt.order_by(Scenario.created_at.desc())

    async def get_review_counts(
        self, scenario_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        """Count reviews for many scenarios in one query."""
        stmt = (
            select(ScenarioReview.scenario_id, func.count())
            .where(ScenarioReview.scenario_id.in_(scenario_ids))
            .group_by(ScenarioReview.scenario_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {scenario_id: count for scenario_id, count in rows}

    async def count_creator_scenarios_by_status(
        self, creator_id: uuid.UUID
    ) -> dict[str, int]:
        """Count a creator's scenarios grouped by raw status."""
        stmt = (
            select(Scenario.status, func.count())
            .where(Scenario.creator_id == creator_id)
            .group_by(Scenario.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {status: count for status, count in rows}

    async def get_creator_card(self, creator_id: uuid.UUID) -> CreatorCard | None:
        """Fetch the public creator fields shown on the scenario page."""
        stmt = select(User.display_name, User.avatar_url, User.bio).where(
            User.user_id == creator_id
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        return CreatorCard(display_name=row[0], avatar_url=row[1], bio=row[2])

    async def count_other_published_by_creator(
        self, creator_id: uuid.UUID, excluded_scenario_id: uuid.UUID
    ) -> int:
        """Count a creator's published scenarios other than the given one."""
        stmt = select(func.count()).where(
            Scenario.creator_id == creator_id,
            Scenario.status == "published",
            Scenario.visibility == PUBLIC_VISIBILITY,
            Scenario.scenario_id != excluded_scenario_id,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def get_rating_counts(self, scenario_id: uuid.UUID) -> dict[int, int]:
        """Count reviews per star rating across all reviews of a scenario."""
        stmt = (
            select(ScenarioReview.rating, func.count())
            .where(ScenarioReview.scenario_id == scenario_id)
            .group_by(ScenarioReview.rating)
        )
        rows = (await self.session.execute(stmt)).all()
        return {rating: count for rating, count in rows}

    async def get_creator_display_names(
        self, creator_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str | None]:
        """Fetch display names for many creators in one query."""
        stmt = select(User.user_id, User.display_name).where(
            User.user_id.in_(creator_ids)
        )
        res = await self.session.execute(stmt)
        return {user_id: name for user_id, name in res.all()}

    async def get_bookmarked_scenario_ids(
        self, user_id: uuid.UUID, scenario_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        """Return which of the given scenarios the user has bookmarked."""
        stmt = select(Bookmark.scenario_id).where(
            Bookmark.user_id == user_id, Bookmark.scenario_id.in_(scenario_ids)
        )
        res = await self.session.execute(stmt)
        return set(res.scalars().all())

    async def is_bookmarked(self, user_id: uuid.UUID, scenario_id: uuid.UUID) -> bool:
        """Check if user has bookmarked a scenario."""
        stmt = select(Bookmark).where(
            Bookmark.user_id == user_id, Bookmark.scenario_id == scenario_id
        )
        res = await self.session.execute(stmt)
        return res.scalars().first() is not None

    async def add_bookmark(self, user_id: uuid.UUID, scenario_id: uuid.UUID) -> None:
        """Add scenario bookmark for user if not existing."""
        if not await self.is_bookmarked(user_id, scenario_id):
            bm = Bookmark(user_id=user_id, scenario_id=scenario_id)
            self.session.add(bm)
            await self.session.flush()

    async def remove_bookmark(self, user_id: uuid.UUID, scenario_id: uuid.UUID) -> None:
        """Remove scenario bookmark for user."""
        stmt = select(Bookmark).where(
            Bookmark.user_id == user_id, Bookmark.scenario_id == scenario_id
        )
        res = await self.session.execute(stmt)
        bm = res.scalars().first()
        if bm:
            await self.session.delete(bm)
            await self.session.flush()

    async def has_user_played_min_turns(
        self, user_id: uuid.UUID, scenario_id: uuid.UUID, min_turns: int = 10
    ) -> bool:
        """Check if user has a non-playtest playthrough for scenario with at
        least min_turns. Playtest playthroughs are excluded so a creator
        cannot farm their own review eligibility by playtesting a draft.
        """
        stmt = select(Playthrough).where(
            Playthrough.created_by == user_id,
            Playthrough.scenario_id == scenario_id,
            Playthrough.turn_count >= min_turns,
            Playthrough.is_playtest.is_(False),
        )
        res = await self.session.execute(stmt)
        return res.scalars().first() is not None

    async def list_reviews(
        self, scenario_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[tuple[ScenarioReview, str]], int, float]:
        """Fetch reviews for a scenario with user display names."""
        stmt = (
            select(ScenarioReview, User.display_name)
            .join(User, ScenarioReview.user_id == User.user_id)
            .where(ScenarioReview.scenario_id == scenario_id)
            .order_by(ScenarioReview.created_at.desc(), ScenarioReview.review_id.desc())
        )
        count_stmt = select(func.count()).select_from(
            select(ScenarioReview)
            .where(ScenarioReview.scenario_id == scenario_id)
            .subquery()
        )
        avg_stmt = select(func.avg(ScenarioReview.rating)).where(
            ScenarioReview.scenario_id == scenario_id
        )
        total = (await self.session.execute(count_stmt)).scalar_one() or 0
        avg_val = (await self.session.execute(avg_stmt)).scalar_one() or 0.0

        paginated_stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(paginated_stmt)
        return list(res.all()), total, float(avg_val)

    async def get_user_review(
        self, user_id: uuid.UUID, scenario_id: uuid.UUID
    ) -> tuple[ScenarioReview, str] | None:
        """Fetch one user's review of a scenario with their display name."""
        stmt = (
            select(ScenarioReview, User.display_name)
            .join(User, ScenarioReview.user_id == User.user_id)
            .where(
                ScenarioReview.scenario_id == scenario_id,
                ScenarioReview.user_id == user_id,
            )
        )
        row = (await self.session.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    async def create_or_update_review(
        self,
        user_id: uuid.UUID,
        scenario_id: uuid.UUID,
        rating: int,
        comment: str | None,
    ) -> tuple[ScenarioReview, str]:
        """Create or update user review for a scenario and update scenario rating_avg."""
        stmt = select(ScenarioReview).where(
            ScenarioReview.user_id == user_id, ScenarioReview.scenario_id == scenario_id
        )
        res = await self.session.execute(stmt)
        review = res.scalars().first()
        if review:
            review.rating = rating
            review.comment = comment
        else:
            review = ScenarioReview(
                user_id=user_id, scenario_id=scenario_id, rating=rating, comment=comment
            )
            self.session.add(review)
        await self.session.flush()

        # NOTE: Lock the scenario row before computing the average, not
        # after: a concurrent reviewer's transaction must block here until
        # this one commits, so its own average recomputation sees this
        # review too. Locking after computing the average would let two
        # concurrent reviews both average from the same pre-commit snapshot
        # and overwrite each other's result.
        scen = await self.get_by_id_for_update(scenario_id)
        avg_stmt = select(func.avg(ScenarioReview.rating)).where(
            ScenarioReview.scenario_id == scenario_id
        )
        new_avg = (await self.session.execute(avg_stmt)).scalar_one() or 0.0
        if scen:
            scen.rating_avg = round(Decimal(str(new_avg)), 2)
            await self.session.flush()

        user_stmt = select(User.display_name).where(User.user_id == user_id)
        user_res = await self.session.execute(user_stmt)
        display_name = user_res.scalar_one_or_none() or "Adventurer"

        return review, display_name

    async def list_public_playthroughs(
        self, scenario_id: uuid.UUID, limit: int = 10
    ) -> list[tuple[Playthrough, str]]:
        """List active or completed playthroughs with player display names."""
        stmt = (
            select(Playthrough, User.display_name)
            .join(User, Playthrough.created_by == User.user_id)
            .where(Playthrough.scenario_id == scenario_id)
            .where(Playthrough.is_playtest.is_(False))
            .order_by(Playthrough.updated_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.all())
