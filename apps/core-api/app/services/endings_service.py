"""Per-story ending progress for the owner's Endings tab, Overview and scenario page."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from app.db.models.end_condition import EndCondition
from app.db.models.scenario import Scenario
from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.models.endings import EndingsResponse
from app.models.scenario_endings import FoundEndingResponse, ScenarioEndingsResponse
from app.repositories.end_condition_repo import EndConditionRepo
from app.repositories.endings_repo import (
    EndedRunDetailRow,
    EndedRunRow,
    EndingsRepo,
    SnapshotEndingsRow,
)
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.endings_builder import build_scenario_endings
from app.services.scenario_access import ScenarioAccessChecker


def _condition_as_snapshot_entry(condition: EndCondition) -> dict[str, object]:
    return {
        "end_condition_id": str(condition.end_condition_id),
        "outcome_tag": condition.outcome_tag,
        "outcome_title": condition.outcome_title,
        "is_secret": condition.is_secret,
        "priority": condition.priority,
    }


def _to_found_endings(runs: list[EndedRunDetailRow]) -> list[FoundEndingResponse]:
    """One entry per distinct ending, keeping the earliest run that reached it."""
    first_by_ending: dict[tuple[str, str], EndedRunDetailRow] = {}
    for run in runs:
        key = (
            ("id", str(run.outcome_id))
            if run.outcome_id
            else ("title", run.outcome_title)
        )
        first_by_ending.setdefault(key, run)
    return [
        FoundEndingResponse(
            ending_id=run.outcome_id,
            title=run.outcome_title,
            text=run.outcome_text,
            outcome_tag=run.outcome_tag,
            turn_reached=run.turn_count,
            found_at=run.ended_at or datetime.now(UTC),
        )
        for run in first_by_ending.values()
    ]


class EndingsService:
    """Builds found/total ending slots from finished runs and latest snapshots."""

    def __init__(
        self,
        endings_repo: EndingsRepo,
        end_condition_repo: EndConditionRepo | None = None,
        scenario_repo: ScenarioRepo | None = None,
    ) -> None:
        self.endings_repo = endings_repo
        session = endings_repo.session
        self.end_condition_repo = end_condition_repo or EndConditionRepo(session)
        self.scenario_repo = scenario_repo or ScenarioRepo(session)
        self.access = ScenarioAccessChecker(ScenarioAccessRepo(session))

    async def get_endings(self, user_id: uuid.UUID) -> EndingsResponse:
        """Return the owner's endings progress; never writes."""
        snapshots = await self.endings_repo.list_latest_snapshot_endings(user_id)
        runs_by_scenario: dict[uuid.UUID, list[EndedRunRow]] = defaultdict(list)
        for run in await self.endings_repo.list_ended_runs(user_id):
            runs_by_scenario[run.scenario_id].append(run)
        scenarios = [
            built
            for snapshot in snapshots
            if (
                built := build_scenario_endings(
                    snapshot, runs_by_scenario[snapshot.scenario_id]
                )
            )
        ]
        return EndingsResponse(scenarios=scenarios)

    async def get_scenario_endings(
        self, scenario_id: uuid.UUID, viewer_id: uuid.UUID | None
    ) -> ScenarioEndingsResponse:
        """Endings count for anyone; the viewer's own found endings when signed in.

        Unfound endings are never described, and unfound secret endings are not
        counted, so the total cannot leak that a hidden ending exists.
        """
        scenario = await self._get_visible_scenario(scenario_id, viewer_id)
        conditions = await self.end_condition_repo.list_by_scenario(scenario_id)
        runs = (
            await self.endings_repo.list_ended_run_details(viewer_id, scenario_id)
            if viewer_id
            else []
        )
        snapshot = SnapshotEndingsRow(
            scenario_id,
            scenario.title,
            datetime.now(UTC),
            [_condition_as_snapshot_entry(condition) for condition in conditions],
        )
        built = build_scenario_endings(snapshot, runs)
        return ScenarioEndingsResponse(
            total_count=built.total_count if built else 0,
            found=_to_found_endings(runs) if viewer_id else None,
        )

    async def _get_visible_scenario(
        self, scenario_id: uuid.UUID, viewer_id: uuid.UUID | None
    ) -> Scenario:
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()
        is_hidden_draft = (
            scenario.status == "draft" and scenario.creator_id != viewer_id
        )
        if is_hidden_draft:
            raise ScenarioNotFoundError()
        await self.access.ensure_can_open(scenario, viewer_id)
        return scenario
