"""Map generation job data repository for direct database operations."""

import uuid

from app.db.models.map_generation_job import MapGenerationJob
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ACTIVE_STATUSES = ("pending", "running")


class MapGenerationJobRepo:
    """Repository managing direct SQLAlchemy queries for MapGenerationJob."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, scenario_id: uuid.UUID, creator_id: uuid.UUID, description: str
    ) -> MapGenerationJob:
        job = MapGenerationJob(
            scenario_id=scenario_id,
            creator_id=creator_id,
            description=description,
            status="pending",
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> MapGenerationJob | None:
        stmt = select(MapGenerationJob).where(MapGenerationJob.job_id == job_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_latest_for_scenario(
        self, scenario_id: uuid.UUID
    ) -> MapGenerationJob | None:
        stmt = (
            select(MapGenerationJob)
            .where(MapGenerationJob.scenario_id == scenario_id)
            .order_by(MapGenerationJob.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def mark_running(self, job_id: uuid.UUID) -> None:
        job = await self.get_by_id(job_id)
        if job is None:
            return
        job.status = "running"
        await self.session.flush()

    async def mark_succeeded(
        self,
        job_id: uuid.UUID,
        region_image_url: str,
        picture_url: str | None,
        width: int,
        height: int,
    ) -> None:
        job = await self.get_by_id(job_id)
        if job is None:
            return
        job.status = "succeeded"
        job.region_image_url = region_image_url
        job.picture_url = picture_url
        job.has_art = picture_url is not None
        job.width = width
        job.height = height
        await self.session.flush()

    async def mark_failed(self, job_id: uuid.UUID, error_message: str) -> None:
        job = await self.get_by_id(job_id)
        if job is None:
            return
        job.status = "failed"
        job.error_message = error_message
        await self.session.flush()
