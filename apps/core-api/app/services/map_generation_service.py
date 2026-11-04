"""Strategy map generation: a flat-color region image, then painted art for it."""

import asyncio
import uuid
from datetime import UTC, datetime
from io import BytesIO

import structlog
from app.config import settings
from app.db.models.map_generation_job import MapGenerationJob
from app.db.models.user import User
from app.exceptions.base import BaseAppException
from app.exceptions.map_generation_exceptions import (
    InvalidRegionImageError,
    MapJobNotFoundError,
)
from app.exceptions.upload_exceptions import ImageGenerationError
from app.integrations import image_gen_client, storage_client
from app.models.map_generation import (
    GeneratedMapArt,
    GeneratedRegionImage,
    MapGenerationJobResponse,
)
from app.repositories.map_generation_job_repo import (
    ACTIVE_STATUSES,
    MapGenerationJobRepo,
)
from app.repositories.user_repo import UserRepo
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService, quota_scope
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger()

EVENT_MAP_JOB_SUCCEEDED = "map_generation_job_succeeded"
EVENT_MAP_JOB_FAILED = "map_generation_job_failed"
EVENT_MAP_JOB_ART_FELL_BACK = "map_generation_job_art_fell_back"
MAP_JOB_STALE_SECONDS = 600
MAP_JOB_INTERRUPTED_MESSAGE = "Map generation was interrupted. Try again."
MAP_JOB_GENERIC_FAILURE_MESSAGE = "Map generation failed. Try again."

MAX_REGION_PNG_BYTES = 5 * 1024 * 1024
MAX_REGION_IMAGE_PIXELS = 4096 * 4096
REGION_IMAGE_SIZE_REQUEST = "1024x768"
MAP_OBJECT_PREFIX = "scenario-maps"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_CONTENT_TYPE = "image/png"
WEBP_CONTENT_TYPE = "image/webp"
ART_WEBP_QUALITY = 90

_REGION_PROMPT = (
    'Flat-color political region map of the world described as: "{description}". '
    "Top-down view on a flat solid sea. Draw about 30 land regions that tile the "
    "land with no gaps, each region filled with ONE solid, saturated color, and "
    "every pair of neighbouring regions a clearly distinct hue. The sea is a "
    "single flat solid color. No text, no labels, no outlines, no borders, no "
    "gradients, no shading, no texture, no icons, no legend."
)
_ART_PROMPT = (
    "Repaint this flat-color region map as a soft, hand-painted watercolor "
    'fantasy map on light warm parchment paper with visible paper grain. Theme: "{description}". '
    "Use only pale, muted, desaturated washes in one cohesive natural palette "
    "(sand, sage, soft ochre, pale blue-grey). Do NOT keep the bright region colors. "
    "Paint terrain loosely as washes with gentle brush marks (low hills, forests, "
    "marsh, rivers), not as repeated icons. Keep the coastline, lakes and the "
    "position and size of every shape exactly identical to the input. "
    "No text, no labels, no names, no compass, no legend, no frame, no border, "
    "no decorative ornament. Draw no lines between regions. The sea is a pale "
    "grey-blue mist wash with no wave pattern, fading softly at the coast."
)


def build_region_prompt(description: str) -> str:
    return _REGION_PROMPT.format(description=description)


def build_art_prompt(description: str) -> str:
    return _ART_PROMPT.format(description=description)


def webp_to_png(content: bytes) -> bytes:
    buffer = BytesIO()
    Image.open(BytesIO(content)).convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def resize_to_match(art: bytes, target: tuple[int, int]) -> bytes:
    """Resample Muse's slightly enlarged edit back to the region image's size."""
    try:
        image = Image.open(BytesIO(art))
        if image.size == target:
            return art
        buffer = BytesIO()
        resized = image.convert("RGB").resize(target, Image.Resampling.BILINEAR)
        resized.save(buffer, format="WEBP", quality=ART_WEBP_QUALITY)
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageGenerationError("Image generation returned bad data") from exc
    return buffer.getvalue()


def _read_png_size(content: bytes) -> tuple[int, int]:
    if not content.startswith(PNG_SIGNATURE) or len(content) > MAX_REGION_PNG_BYTES:
        raise InvalidRegionImageError()
    try:
        image = Image.open(BytesIO(content))
        width, height = image.size
        if width * height > MAX_REGION_IMAGE_PIXELS:
            raise InvalidRegionImageError("The region image has too many pixels")
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidRegionImageError() from exc
    return width, height


class MapGenerationService:
    """Generates strategy map region images and painted art with Meta Muse Image."""

    def __init__(
        self,
        quota_service: QuotaService | None,
        job_repo: MapGenerationJobRepo | None = None,
    ) -> None:
        self.quota_service = quota_service
        self.job_repo = job_repo

    async def generate_region_image(
        self, description: str, user: User
    ) -> GeneratedRegionImage:
        """Generate, store and describe a flat-color region image."""
        _, region = await self._render_region_image(description, user)
        return region

    def _require_job_repo(self) -> MapGenerationJobRepo:
        if self.job_repo is None:
            raise RuntimeError("MapGenerationService was built without a job repo")
        return self.job_repo

    async def _render_region_image(
        self, description: str, user: User
    ) -> tuple[bytes, GeneratedRegionImage]:
        async with quota_scope(self.quota_service, QuotaFeature.COVER_IMAGE, user):
            webp = await image_gen_client.generate_image(
                build_region_prompt(description),
                settings.image_generation_timeout_seconds,
                size=REGION_IMAGE_SIZE_REQUEST,
            )
            png = await asyncio.to_thread(webp_to_png, webp)
            width, height = await asyncio.to_thread(_read_png_size, png)
            url = await self._store(png, PNG_CONTENT_TYPE, ".png")
        return png, GeneratedRegionImage(
            region_image_url=url, width=width, height=height
        )

    async def generate_art(
        self, region_png: bytes, description: str, user: User
    ) -> GeneratedMapArt:
        """Paint a watercolor picture for a region image, at the same size."""
        size = await asyncio.to_thread(_read_png_size, region_png)
        async with quota_scope(self.quota_service, QuotaFeature.COVER_IMAGE, user):
            edited = await image_gen_client.edit_image(
                build_art_prompt(description),
                region_png,
                PNG_CONTENT_TYPE,
                settings.image_generation_timeout_seconds,
            )
            art = await asyncio.to_thread(resize_to_match, edited, size)
            url = await self._store(art, WEBP_CONTENT_TYPE, ".webp")
        return GeneratedMapArt(picture_url=url, width=size[0], height=size[1])

    async def _store(self, content: bytes, content_type: str, extension: str) -> str:
        object_key = f"{MAP_OBJECT_PREFIX}/{uuid.uuid4()}{extension}"
        return await storage_client.upload_image(content, content_type, object_key)

    async def request_generation(
        self, scenario_id: uuid.UUID, creator: User, description: str
    ) -> tuple[MapGenerationJobResponse, bool]:
        """Create a pending job, or return the scenario's live one.

        The boolean is True only when a new job was created, so the caller
        schedules the background run exactly once per job.
        """
        job_repo = self._require_job_repo()
        latest = await job_repo.get_latest_for_scenario(scenario_id)
        if latest is not None and latest.status in ACTIVE_STATUSES:
            if not _is_stale(latest):
                return MapGenerationJobResponse.model_validate(latest), False
            await job_repo.mark_failed(latest.job_id, MAP_JOB_INTERRUPTED_MESSAGE)
        job = await job_repo.create(scenario_id, creator.user_id, description)
        return MapGenerationJobResponse.model_validate(job), True

    async def get_latest_job(
        self, scenario_id: uuid.UUID, creator_id: uuid.UUID
    ) -> MapGenerationJobResponse:
        job_repo = self._require_job_repo()
        job = await job_repo.get_latest_for_scenario(scenario_id)
        if job is None or job.creator_id != creator_id:
            raise MapJobNotFoundError()
        return await self._with_stale_check(job)

    async def get_job_status(
        self, scenario_id: uuid.UUID, job_id: uuid.UUID, creator_id: uuid.UUID
    ) -> MapGenerationJobResponse:
        job_repo = self._require_job_repo()
        job = await job_repo.get_by_id(job_id)
        if (
            job is None
            or job.creator_id != creator_id
            or job.scenario_id != scenario_id
        ):
            raise MapJobNotFoundError()
        return await self._with_stale_check(job)

    async def _with_stale_check(
        self, job: MapGenerationJob
    ) -> MapGenerationJobResponse:
        job_repo = self._require_job_repo()
        if job.status in ACTIVE_STATUSES and _is_stale(job):
            await job_repo.mark_failed(job.job_id, MAP_JOB_INTERRUPTED_MESSAGE)
        return MapGenerationJobResponse.model_validate(job)

    @staticmethod
    async def run_generation_job(
        job_id: uuid.UUID,
        session_factory: async_sessionmaker[AsyncSession],
        quota_service: QuotaService | None = None,
    ) -> None:
        """Render the region image, then the art, against the job's own session."""
        async with session_factory() as session:
            job_repo = MapGenerationJobRepo(session)
            service = MapGenerationService(quota_service, job_repo)
            job = await job_repo.get_by_id(job_id)
            creator = await UserRepo(session).get_by_id(job.creator_id) if job else None
            if job is None or creator is None:
                return
            description = job.description
            await job_repo.mark_running(job_id)
            await session.commit()
            await service._finish_job(session, job_id, description, creator)

    async def _finish_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        description: str,
        creator: User,
    ) -> None:
        job_repo = self._require_job_repo()
        # NOTE: Intentionally broad. This is the terminal handler of a
        # background job; an unanticipated exception type escaping here would
        # leave the job "running" forever instead of failed with a message.
        try:
            png, region = await self._render_region_image(description, creator)
            picture_url = await self._paint_art_or_none(png, description, creator)
        except Exception as exc:  # noqa: BLE001 - recorded as the job error
            message = (
                exc.message
                if isinstance(exc, BaseAppException)
                else MAP_JOB_GENERIC_FAILURE_MESSAGE
            )
            await job_repo.mark_failed(job_id, message)
            logger.warning(EVENT_MAP_JOB_FAILED, job_id=str(job_id), error=str(exc))
            await session.commit()
            return
        await job_repo.mark_succeeded(
            job_id, region.region_image_url, picture_url, region.width, region.height
        )
        logger.info(EVENT_MAP_JOB_SUCCEEDED, job_id=str(job_id))
        await session.commit()

    async def _paint_art_or_none(
        self, png: bytes, description: str, creator: User
    ) -> str | None:
        """Painted art is optional: a failed edit leaves the flat region image."""
        try:
            art = await self.generate_art(png, description, creator)
        except ImageGenerationError as exc:
            logger.warning(EVENT_MAP_JOB_ART_FELL_BACK, error=str(exc))
            return None
        return art.picture_url


def _is_stale(job: MapGenerationJob) -> bool:
    age = datetime.now(UTC) - job.updated_at
    return age.total_seconds() > MAP_JOB_STALE_SECONDS
