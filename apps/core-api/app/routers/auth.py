from app.config import settings
from app.db.connection import get_db_session
from app.exceptions.auth_exceptions import InvalidTokenError
from app.models.auth import TokenExchangeRequest, TokenResponse, UserResponse
from app.repositories.alpha_invite_repo import AlphaInviteRepo
from app.repositories.user_repo import UserRepo
from app.services.alpha_invite_service import AlphaInviteService
from app.services.auth_service import AuthService
from app.services.rate_limit.client_identity import resolve_client_ip
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/auth", tags=["auth"])

# NOTE: must match the URL path the BROWSER actually requests, which is not
# fixed across environments: production's frontend nginx forwards /api/* to
# this service with the /api prefix stripped, so browsers there see
# "/api/v1/auth/refresh" -- but local dev (docker-compose.dev.yml) points the
# Vite dev server straight at this service with no prefix at all, so browsers
# there see "/v1/auth/refresh". A cookie Path scoped to either one specifically
# breaks in the other topology: the browser silently never attaches it and
# every refresh looks like a missing token, forcing a fresh login on every
# access-token expiry instead of a silent refresh (confirmed live in local
# dev -- see docs/reports/auth-security-audit-report.md Finding 8). "/" is the
# only path that's correct regardless of which prefix convention is in front.
REFRESH_TOKEN_COOKIE_PATH = "/"


def get_auth_service(
    session: AsyncSession = Depends(get_db_session, scope="function"),
    quota_service: QuotaService = Depends(get_quota_service),
) -> AuthService:
    return AuthService(
        UserRepo(session),
        quota_service,
        AlphaInviteService(AlphaInviteRepo(session)),
    )


@router.post("/token", response_model=TokenResponse)
async def exchange_token(
    req: TokenExchangeRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    user = await auth_service.verify_firebase_token_and_upsert_user(
        req.firebase_id_token,
        client_ip=resolve_client_ip(request),
        invite_code=req.invite_code,
        alpha_consent_version=req.alpha_consent_version,
    )

    is_restored = await auth_service.restore_if_deletion_pending(user)
    access_token = auth_service.generate_access_token(user)
    refresh_token = await auth_service.generate_refresh_token(user)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        path=REFRESH_TOKEN_COOKIE_PATH,
        max_age=settings.jwt_refresh_expire_days * 24 * 60 * 60,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
        user=UserResponse.model_validate(user),
        is_account_restored=is_restored,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
):
    if not refresh_token:
        raise InvalidTokenError("Refresh token missing")

    access_token, new_refresh_token, user = await auth_service.refresh_tokens(
        refresh_token
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        path=REFRESH_TOKEN_COOKIE_PATH,
        max_age=settings.jwt_refresh_expire_days * 24 * 60 * 60,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    await auth_service.revoke_session(refresh_token)
    response.delete_cookie(
        key="refresh_token",
        path=REFRESH_TOKEN_COOKIE_PATH,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
    )
