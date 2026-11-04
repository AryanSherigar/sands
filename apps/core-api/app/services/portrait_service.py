"""Studio leader portrait generation with Meta Muse Image."""

import uuid

from app.config import settings
from app.db.models.user import User
from app.integrations import image_gen_client, storage_client
from app.models.portrait_generation import GeneratedPortrait
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService, quota_scope

PORTRAIT_OBJECT_PREFIX = "leader-portraits"
NO_TEXT_INSTRUCTION = "No text or lettering in the image."


def build_portrait_prompt(prompt: str) -> str:
    return f"{prompt} {NO_TEXT_INSTRUCTION}"


class PortraitService:
    """Generates a leader portrait a creator can approve and optionally animate."""

    def __init__(self, quota_service: QuotaService | None) -> None:
        self.quota_service = quota_service

    async def generate_portrait(self, prompt: str, user: User) -> GeneratedPortrait:
        async with quota_scope(self.quota_service, QuotaFeature.COVER_IMAGE, user):
            image_bytes = await image_gen_client.generate_image(
                build_portrait_prompt(prompt), settings.image_generation_timeout_seconds
            )
            object_key = (
                f"{PORTRAIT_OBJECT_PREFIX}/{uuid.uuid4()}"
                f"{image_gen_client.output_extension()}"
            )
            url = await storage_client.upload_image(
                image_bytes, image_gen_client.output_content_type(), object_key
            )
        return GeneratedPortrait(image_url=url)
