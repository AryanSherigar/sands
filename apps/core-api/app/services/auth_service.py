import uuid
from datetime import datetime, timedelta, timezone

import jwt
import structlog
from app.config import settings
from app.db.models.user import User
from app.exceptions.alpha_exceptions import (
    AccountSuspendedError,
    AlphaConsentRequiredError,
    AlphaInviteRequiredError,
    AlphaSignupClosedError,
)
from app.exceptions.auth_exceptions import InvalidTokenError
from app.repositories.user_repo import UserRepo
from app.services.alpha_consent import log_alpha_consent_recorded
from app.services.alpha_invite_service import (
    EVENT_ALPHA_SIGNUP_REFUSED,
    AlphaInviteService,
)
from app.services.rate_limit.quota_service import QuotaService
from firebase_admin import auth as firebase_auth
from firebase_admin import exceptions as firebase_exceptions
from google.auth import exceptions as google_auth_exceptions

logger = structlog.get_logger()

EVENT_AUTH_DEV_BYPASS_USED = "auth_dev_bypass_used"
EVENT_AUTH_TOKEN_VERIFICATION_FAILED = "auth_token_verification_failed"
EVENT_AUTH_TOKEN_REFRESH_DENIED = "auth_token_refresh_denied"
EVENT_AUTH_TOKEN_REFRESH_GRACE_REPLAY = "auth_token_refresh_grace_replay"
EVENT_AUTH_SUSPENDED_USER_REFUSED = "auth_suspended_user_refused"
REASON_SIGNUP_CLOSED = "signup_closed"
REASON_CONSENT_MISSING = "consent_missing"
REASON_INVITE_MISSING = "invite_required"


class AuthService:
    def __init__(
        self,
        user_repo: UserRepo,
        quota_service: QuotaService | None = None,
        alpha_invite_service: AlphaInviteService | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.quota_service = quota_service
        self.alpha_invite_service = alpha_invite_service

    async def verify_firebase_token_and_upsert_user(
        self,
        firebase_token: str,
        client_ip: str | None = None,
        invite_code: str | None = None,
        alpha_consent_version: str | None = None,
    ) -> User:
        is_dev_or_testing = settings.environment in ("development", "testing")
        if is_dev_or_testing and (
            firebase_token == "mock-dev-token" or not settings.firebase_project_id
        ):
            logger.info(EVENT_AUTH_DEV_BYPASS_USED)
            return await self._upsert_user(
                "dev-firebase-id-123",
                "Dev User",
                None,
                invite_code,
                alpha_consent_version,
            )

        try:
            if settings.firebase_credentials_path or settings.environment == "testing":
                decoded_token = firebase_auth.verify_id_token(firebase_token)
            else:
                from google.auth.transport import requests as google_requests
                from google.oauth2 import id_token as google_id_token

                req = google_requests.Request()
                decoded_token = google_id_token.verify_firebase_token(
                    firebase_token, req, audience=settings.firebase_project_id
                )

            uid = decoded_token.get("uid") or decoded_token.get("sub") or ""
            email = decoded_token.get("email", "")
            name = decoded_token.get("name") or (
                email.split("@")[0] if email else "User"
            )
            return await self._upsert_user(
                uid, name, client_ip, invite_code, alpha_consent_version
            )
        except (
            firebase_exceptions.FirebaseError,
            google_auth_exceptions.GoogleAuthError,
            ValueError,
        ) as e:
            logger.warning(EVENT_AUTH_TOKEN_VERIFICATION_FAILED, error=str(e))
            raise InvalidTokenError(f"Firebase token verification failed: {e!s}") from e

    async def _upsert_user(
        self,
        auth_provider_id: str,
        display_name: str,
        client_ip: str | None = None,
        invite_code: str | None = None,
        alpha_consent_version: str | None = None,
    ) -> User:
        user = await self.user_repo.get_by_auth_provider_id(auth_provider_id)
        if user:
            self._assert_not_suspended(user)
            return user
        if not settings.is_alpha_mode:
            await self._reserve_account_slot(client_ip)
            return await self.user_repo.create(auth_provider_id, display_name)
        return await self._create_alpha_user(
            auth_provider_id,
            display_name,
            client_ip,
            invite_code,
            alpha_consent_version,
        )

    async def _create_alpha_user(
        self,
        auth_provider_id: str,
        display_name: str,
        client_ip: str | None,
        invite_code: str | None,
        alpha_consent_version: str | None,
    ) -> User:
        self._assert_signup_open()
        self._assert_consent_current(alpha_consent_version)
        invite_code = self._require_invite_code(invite_code)
        await self._reserve_account_slot(client_ip)
        invite_id = await self.alpha_invite_service.redeem(invite_code)
        user = await self.user_repo.create(
            auth_provider_id,
            display_name,
            alpha_consent_version=alpha_consent_version,
        )
        await self.alpha_invite_service.record_redemption(invite_id, user.user_id)
        log_alpha_consent_recorded(user.user_id, alpha_consent_version)
        return user

    async def _reserve_account_slot(self, client_ip: str | None) -> None:
        if self.quota_service is not None and client_ip is not None:
            await self.quota_service.reserve_account_creation(client_ip)

    @staticmethod
    def _assert_not_suspended(user: User) -> None:
        if user.alpha_suspended_at is not None:
            logger.warning(EVENT_AUTH_SUSPENDED_USER_REFUSED)
            raise AccountSuspendedError()

    @staticmethod
    def _assert_signup_open() -> None:
        if not settings.is_alpha_signup_enabled:
            logger.warning(EVENT_ALPHA_SIGNUP_REFUSED, reason=REASON_SIGNUP_CLOSED)
            raise AlphaSignupClosedError()

    @staticmethod
    def _assert_consent_current(alpha_consent_version: str | None) -> None:
        if alpha_consent_version != settings.alpha_consent_version:
            logger.warning(EVENT_ALPHA_SIGNUP_REFUSED, reason=REASON_CONSENT_MISSING)
            raise AlphaConsentRequiredError()

    @staticmethod
    def _require_invite_code(invite_code: str | None) -> str:
        if not invite_code:
            logger.warning(EVENT_ALPHA_SIGNUP_REFUSED, reason=REASON_INVITE_MISSING)
            raise AlphaInviteRequiredError()
        return invite_code

    async def restore_if_deletion_pending(self, user: User) -> bool:
        """Cancel a pending account deletion on sign-in; True when restored."""
        if user.deletion_requested_at is None:
            return False
        await self.user_repo.clear_deletion_request(user)
        logger.info("account_deletion_cancelled", user_id=str(user.user_id))
        return True

    async def get_or_create_dev_user(self, user_id: uuid.UUID) -> User:
        """Dev/testing-only auto-provisioning for the x-dev-user-id header.
        Never reachable in production (gated by settings.environment at the
        call site in middleware.auth). Commits immediately so the row is
        visible to any subsequent query within the same request."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            user = await self.user_repo.create_with_id(
                user_id, f"dev_{user_id}", "Dev User"
            )
            await self.user_repo.session.commit()
        return user

    async def get_user_for_access_token(
        self, user_id: uuid.UUID, token_version: int | None
    ) -> User | None:
        """Resolve the user behind a decoded access-token's claims, or None
        if the user no longer exists or token_version has been rotated."""
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.token_version != token_version:
            return None
        self._assert_not_suspended(user)
        return user

    def generate_access_token(self, user: User) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_expire_minutes
        )
        to_encode = {
            "sub": str(user.user_id),
            "exp": expire,
            "token_version": user.token_version,
            "type": "access",
        }
        return jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.jwt_algorithm
        )

    async def generate_refresh_token(self, user: User) -> str:
        """Issue a fresh refresh token and record its jti as the user's only
        valid one. The jti it replaces stays acceptable for the rotation grace
        window so a lost refresh response does not end the session."""
        jti = str(uuid.uuid4())
        user.previous_refresh_jti = user.current_refresh_jti
        user.refresh_rotated_at = datetime.now(timezone.utc)
        user.current_refresh_jti = jti
        await self.user_repo.update(user)
        return self._encode_refresh_token(user, jti)

    def _encode_refresh_token(self, user: User, jti: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_expire_days
        )
        to_encode = {
            "sub": str(user.user_id),
            "exp": expire,
            "token_version": user.token_version,
            "type": "refresh",
            "jti": jti,
        }
        return jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.jwt_algorithm
        )

    def _is_within_rotation_grace(self, user: User, jti: str | None) -> bool:
        if not jti or user.previous_refresh_jti != jti or not user.refresh_rotated_at:
            return False
        elapsed = datetime.now(timezone.utc) - user.refresh_rotated_at
        return elapsed <= timedelta(seconds=settings.refresh_rotation_grace_seconds)

    async def revoke_session(self, refresh_token: str | None) -> None:
        """Best-effort session revocation for logout: bump token_version and
        clear current_refresh_jti so the still-live access token and refresh
        token both stop working. Never raises -- a missing or already-invalid
        refresh token just means there's nothing to revoke, not a failure."""
        if not refresh_token:
            return
        try:
            payload = jwt.decode(
                refresh_token, settings.secret_key, algorithms=[settings.jwt_algorithm]
            )
            user = await self.user_repo.get_by_id(uuid.UUID(payload.get("sub")))
        except (jwt.InvalidTokenError, ValueError, TypeError):
            return
        if user is None:
            return
        user.token_version += 1
        user.current_refresh_jti = None
        user.previous_refresh_jti = None
        await self.user_repo.update(user)

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str, User]:
        """Validate a refresh token and rotate it, returning
        (access_token, new_refresh_token, user)."""
        try:
            payload = jwt.decode(
                refresh_token, settings.secret_key, algorithms=[settings.jwt_algorithm]
            )
        except jwt.InvalidTokenError as err:
            raise InvalidTokenError("Invalid or expired refresh token") from err

        if payload.get("type") != "refresh":
            logger.warning(EVENT_AUTH_TOKEN_REFRESH_DENIED, reason="invalid_token_type")
            raise InvalidTokenError("Invalid token type")

        user = await self.user_repo.get_by_id(uuid.UUID(payload.get("sub")))
        if user:
            self._assert_not_suspended(user)
        if not user or user.token_version != payload.get("token_version"):
            logger.warning(
                EVENT_AUTH_TOKEN_REFRESH_DENIED, reason="revoked_or_user_not_found"
            )
            raise InvalidTokenError("Token revoked or user not found")

        jti = payload.get("jti")
        access_token = self.generate_access_token(user)
        if jti and user.current_refresh_jti == jti:
            return access_token, await self.generate_refresh_token(user), user
        if self._is_within_rotation_grace(user, jti):
            logger.info(EVENT_AUTH_TOKEN_REFRESH_GRACE_REPLAY)
            current = str(user.current_refresh_jti)
            return access_token, self._encode_refresh_token(user, current), user
        logger.warning(EVENT_AUTH_TOKEN_REFRESH_DENIED, reason="stale_refresh_jti")
        raise InvalidTokenError("Refresh token already used or rotated")
