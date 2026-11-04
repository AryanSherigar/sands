"""Enable the tape on the existing Night Desk without replacing scenario rows.

Run: python -m scripts.enable_night_desk_welcome
"""

import asyncio

from app.db.connection import AsyncSessionFactory
from app.services.welcome_tape_service import enable_welcome_tape
from scripts.night_desk.ids import SCENARIO_ID


async def main() -> None:
    async with AsyncSessionFactory() as session, session.begin():
        await enable_welcome_tape(session, SCENARIO_ID)


if __name__ == "__main__":
    asyncio.run(main())
