"""Campaign service forwarding custom player ruler to campaign initialization payload."""

from app.services.playthrough_service import (
    PlaythroughService,
)
from app.services.playthrough_service import (
    PlaythroughService as CampaignService,
)

__all__ = ["CampaignService", "PlaythroughService"]
