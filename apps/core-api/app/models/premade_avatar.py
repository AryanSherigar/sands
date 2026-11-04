from pydantic import BaseModel


class PremadeAvatar(BaseModel):
    id: str
    name: str
    style: str
    avatar_url: str
    preview_url: str
    credit: str | None = None


class PremadeAvatarList(BaseModel):
    avatars: list[PremadeAvatar]
