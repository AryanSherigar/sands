"""Builds the pseudonymous alpha data export."""

import uuid

import structlog
from app.config import settings
from app.db.models.turn_metrics import TurnMetrics
from app.logging_config import log_audit_event
from app.models.alpha_export import (
    EventExport,
    FeedbackExport,
    MetricsRowExport,
    NarrationFlagExport,
    SurveyExport,
    ToolCallSummary,
    TranscriptTurnExport,
    TurnMetricsExport,
)
from app.repositories.alpha_export_repo import AlphaExportRepo
from pydantic import BaseModel

logger = structlog.get_logger()

EVENT_ALPHA_DATA_EXPORTED = "alpha_data_exported"
EXPORT_KINDS = ("transcripts", "metrics", "events", "feedback", "surveys")


def _metrics_export(metrics: TurnMetrics) -> TurnMetricsExport:
    return TurnMetricsExport(
        first_token_ms=metrics.first_token_ms,
        generation_ms=metrics.generation_ms,
        total_ms=metrics.total_ms,
        step_durations=metrics.step_durations,
        memory_degraded_reasons=metrics.memory_degraded_reasons,
        memory_retrieval_ms=metrics.memory_retrieval_ms,
        memory_facts_returned=metrics.memory_facts_returned,
        fired_condition_ids=metrics.fired_condition_ids,
        dropped_mutation_count=metrics.dropped_mutation_count,
        dropped_mutation_paths=metrics.dropped_mutation_paths,
        check_outcomes=metrics.check_outcomes,
        stat_snapshot=metrics.stat_snapshot,
        replay_count=metrics.replay_count,
    )


def _tool_call_summaries(tool_calls: list[object]) -> list[ToolCallSummary]:
    return [
        ToolCallSummary(
            tool_name=str(call.get("tool_name", "")),
            is_valid=bool(call.get("is_valid")),
        )
        for call in tool_calls
        if isinstance(call, dict)
    ]


class AlphaExportService:
    def __init__(self, repo: AlphaExportRepo) -> None:
        self._repo = repo

    async def export(
        self,
        kind: str,
        scenario_title: str | None = None,
        last_playthroughs: int | None = None,
    ) -> list[BaseModel]:
        user_ids = await self._repo.list_exportable_user_ids(
            settings.alpha_consent_version
        )
        playthrough_ids = await self._recent_playthrough_ids(
            user_ids, scenario_title, last_playthroughs
        )
        rows = await self._rows_for(kind, user_ids, playthrough_ids) if user_ids else []
        log_audit_event(
            logger, EVENT_ALPHA_DATA_EXPORTED, kind=kind, row_count=len(rows)
        )
        return rows

    async def _recent_playthrough_ids(
        self,
        user_ids: list[uuid.UUID],
        scenario_title: str | None,
        last_playthroughs: int | None,
    ) -> list[uuid.UUID] | None:
        if last_playthroughs is None or not user_ids:
            return None
        return await self._repo.list_recent_playthrough_ids(
            user_ids, scenario_title, last_playthroughs
        )

    async def _rows_for(
        self,
        kind: str,
        user_ids: list[uuid.UUID],
        playthrough_ids: list[uuid.UUID] | None,
    ) -> list[BaseModel]:
        if kind == "transcripts":
            return await self._transcripts(user_ids, playthrough_ids)
        if kind == "metrics":
            return await self._metrics(user_ids, playthrough_ids)
        if kind == "events":
            return await self._events(user_ids, playthrough_ids)
        if kind == "feedback":
            return await self._feedback_and_flags(user_ids, playthrough_ids)
        return await self._surveys(user_ids, playthrough_ids)

    async def _transcripts(
        self,
        user_ids: list[uuid.UUID],
        playthrough_ids: list[uuid.UUID] | None,
    ) -> list[BaseModel]:
        rows = await self._repo.list_turns(user_ids, playthrough_ids)
        return [
            TranscriptTurnExport(
                user_id=run.created_by,
                playthrough_id=turn.playthrough_id,
                playthrough_status=run.status,
                ended_outcome_tag=run.ended_outcome_tag,
                ended_outcome_title=run.ended_outcome_title,
                turn_number=turn.turn_number,
                action_text=turn.action_text,
                action_mode=turn.action_mode,
                narration_text=turn.narration_text,
                tool_calls=_tool_call_summaries(turn.tool_calls),
                location_id=turn.location_id,
                prompt_tokens=turn.prompt_tokens,
                completion_tokens=turn.completion_tokens,
                model_name=turn.model_name,
                created_at=turn.created_at,
                metrics=_metrics_export(metrics) if metrics else None,
            )
            for turn, run, metrics in rows
        ]

    async def _metrics(
        self,
        user_ids: list[uuid.UUID],
        playthrough_ids: list[uuid.UUID] | None,
    ) -> list[BaseModel]:
        rows = await self._repo.list_metrics(user_ids, playthrough_ids)
        return [
            MetricsRowExport(
                user_id=user_id,
                playthrough_id=metrics.playthrough_id,
                turn_number=metrics.turn_number,
                created_at=metrics.created_at,
                **_metrics_export(metrics).model_dump(),
            )
            for metrics, user_id in rows
        ]

    async def _events(
        self,
        user_ids: list[uuid.UUID],
        playthrough_ids: list[uuid.UUID] | None,
    ) -> list[BaseModel]:
        return [
            EventExport.model_validate(event, from_attributes=True)
            for event in await self._repo.list_events(user_ids, playthrough_ids)
        ]

    async def _feedback_and_flags(
        self,
        user_ids: list[uuid.UUID],
        playthrough_ids: list[uuid.UUID] | None,
    ) -> list[BaseModel]:
        feedback = [
            FeedbackExport.model_validate(row, from_attributes=True)
            for row in await self._repo.list_feedback(user_ids, playthrough_ids)
        ]
        flags = [
            NarrationFlagExport.model_validate(row, from_attributes=True)
            for row in await self._repo.list_flags(user_ids, playthrough_ids)
        ]
        return [*feedback, *flags]

    async def _surveys(
        self,
        user_ids: list[uuid.UUID],
        playthrough_ids: list[uuid.UUID] | None,
    ) -> list[BaseModel]:
        return [
            SurveyExport.model_validate(row, from_attributes=True)
            for row in await self._repo.list_surveys(user_ids, playthrough_ids)
        ]
