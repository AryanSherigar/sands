"""Effects a condition asks the client to perform once, after the turn commits."""

from pydantic import BaseModel


class FiredEffect(BaseModel):
    kind: str
    params: dict[str, object]
