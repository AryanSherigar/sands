import base64
import json
import time

import jwt
from app.config import get_settings
from app.middleware.auth import get_current_user
from app.middleware.error_handler import setup_error_handlers
from app.models.auth import CurrentUser
from fastapi import Depends, FastAPI

TEST_SECRET = "test-secret-key-with-more-than-32-chars"
OTHER_SECRET = "a-completely-different-secret-key-value"
USER_ID = "11111111-1111-1111-1111-111111111111"
TOKEN_LIFETIME_SECONDS = 600


def set_settings(monkeypatch, **environment: str) -> None:
    for name, value in environment.items():
        monkeypatch.setenv(name.upper(), value)
    get_settings.cache_clear()


def make_token(
    secret: str = TEST_SECRET, algorithm: str = "HS256", **overrides: object
) -> str:
    claims: dict[str, object] = {
        "sub": USER_ID,
        "type": "access",
        "token_version": 1,
        "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS,
    }
    claims.update(overrides)
    for key in [key for key, value in claims.items() if value is None]:
        del claims[key]
    return jwt.encode(claims, secret, algorithm=algorithm)


def unsigned_token() -> str:
    def encode(part: dict[str, object]) -> str:
        raw = json.dumps(part).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = encode({"alg": "none", "typ": "JWT"})
    payload = encode({"sub": USER_ID, "type": "access", "exp": int(time.time()) + 600})
    return f"{header}.{payload}."


def make_auth_app() -> FastAPI:
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/me")
    async def read_me(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
        return {"user_id": str(user.user_id)}

    return app
