"""Commit test setup before independent pipeline sessions read it."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def committed_factory(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    await session.commit()
    return async_sessionmaker(bind=session.bind, expire_on_commit=False)
