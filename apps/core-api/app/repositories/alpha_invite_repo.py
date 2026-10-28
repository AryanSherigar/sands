"""Alpha invite persistence.

The redeem statement is a single atomic UPDATE so concurrent redeems can never
hand out more than max_seats. Every time comparison uses the database's now()
(ADR-13), never the application clock.
"""

import uuid

from app.db.models.alpha_invite import AlphaInvite, AlphaInviteRedemption
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

UNKNOWN_INVITE_REASON = "unknown_invite"

_REDEEM_SEAT_SQL = text(
    """
    UPDATE alpha_invites
       SET seats_used = seats_used + 1
     WHERE code_hash = :code_hash
       AND revoked_at IS NULL
       AND (expires_at IS NULL OR expires_at > now())
       AND seats_used < max_seats
    RETURNING invite_id
    """
)

_CREATE_INVITE_SQL = text(
    """
    INSERT INTO alpha_invites (code_hash, label, max_seats, expires_at)
    VALUES (
        :code_hash,
        :label,
        :max_seats,
        CASE
            WHEN CAST(:expires_days AS integer) IS NULL THEN NULL
            ELSE now() + make_interval(days => CAST(:expires_days AS integer))
        END
    )
    RETURNING invite_id
    """
)

_REFUSAL_REASON_SQL = text(
    """
    SELECT CASE
        WHEN revoked_at IS NOT NULL THEN 'revoked_invite'
        WHEN expires_at IS NOT NULL AND expires_at <= now() THEN 'expired_invite'
        WHEN seats_used >= max_seats THEN 'full_invite'
        ELSE 'unknown_invite'
    END
    FROM alpha_invites
    WHERE code_hash = :code_hash
    """
)

_REVOKE_BY_LABEL_SQL = text(
    "UPDATE alpha_invites SET revoked_at = now() "
    "WHERE label = :label AND revoked_at IS NULL"
)

_REVOKE_BY_ID_SQL = text(
    "UPDATE alpha_invites SET revoked_at = now() "
    "WHERE invite_id = :invite_id AND revoked_at IS NULL"
)


class AlphaInviteRepo:
    """Repository for alpha invites and their redemptions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def redeem_seat(self, code_hash: str) -> uuid.UUID | None:
        result = await self.session.execute(_REDEEM_SEAT_SQL, {"code_hash": code_hash})
        return result.scalar_one_or_none()

    async def get_refusal_reason(self, code_hash: str) -> str:
        result = await self.session.execute(
            _REFUSAL_REASON_SQL, {"code_hash": code_hash}
        )
        return result.scalar_one_or_none() or UNKNOWN_INVITE_REASON

    async def add_redemption(self, invite_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.session.add(AlphaInviteRedemption(invite_id=invite_id, user_id=user_id))
        await self.session.flush()

    async def get_by_hash(self, code_hash: str) -> AlphaInvite | None:
        stmt = select(AlphaInvite).where(AlphaInvite.code_hash == code_hash)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_invite(
        self,
        code_hash: str,
        label: str,
        max_seats: int,
        expires_days: int | None,
    ) -> AlphaInvite:
        result = await self.session.execute(
            _CREATE_INVITE_SQL,
            {
                "code_hash": code_hash,
                "label": label,
                "max_seats": max_seats,
                "expires_days": expires_days,
            },
        )
        invite_id = result.scalar_one()
        stmt = select(AlphaInvite).where(AlphaInvite.invite_id == invite_id)
        created = await self.session.execute(stmt)
        return created.scalar_one()

    async def list_invites(self) -> list[AlphaInvite]:
        stmt = select(AlphaInvite).order_by(AlphaInvite.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_by_label(self, label: str) -> int:
        result = await self.session.execute(_REVOKE_BY_LABEL_SQL, {"label": label})
        return result.rowcount

    async def revoke_by_id(self, invite_id: uuid.UUID) -> int:
        result = await self.session.execute(_REVOKE_BY_ID_SQL, {"invite_id": invite_id})
        return result.rowcount
