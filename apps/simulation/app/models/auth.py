from uuid import UUID

from app.models.base import WorldModel


class CurrentUser(WorldModel):
    user_id: UUID
