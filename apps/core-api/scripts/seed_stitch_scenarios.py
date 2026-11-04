"""Seed script for canonical Stitch scenarios and playthroughs.

Run via:
    docker exec -i sands-core-api python -m scripts.seed_stitch_scenarios
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.db.connection import AsyncSessionFactory
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from sqlalchemy import select

CREATOR_ID = uuid.UUID("ea1b969a-07e1-41be-a5e7-a74e71c15ed4")
SCOUT_USER_ID = uuid.UUID("4c8cdbb7-bde6-4620-9acf-9da59495b048")

STITCH_SCENARIOS = [
    {
        "scenario_id": uuid.UUID("11111111-2222-3333-4444-555555555551"),
        "title": "The Last Archivist of Oakhaven",
        "logline": "In a dying realm where written history turns to ash, you guard the final repository of forbidden knowledge. Every vow you break alters the world.",
        "mode": "master",
        "complexity_tier": "master",
        "player_count_support": "solo",
        "genre_tags": ["High Fantasy", "Interactive Fiction"],
        "rating_avg": Decimal("4.90"),
        "play_count": 3840,
        "status": "published",
        "estimated_playtime": "45m",
        "cover_image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuCaqmJks5pMWuWqfs1rjZMjAC_gfRkg2mNfRabJH3WuO2zAUUX0E4c3hDwM5AimoMVfTQq0ryrCZ4G066D790mswtyheJ1DDQT46pjZBFGMtWkSjgOVdqqhEf1Rrd9agr23pvocO-42OEPM96v6AIEjrd79wmlBNyJ-cO4rSrDHcq0xq5wttT-N9CBgp_oV00-dGqWNd2Y3JObPODJkXREO2l843spev_jTyY2Crln7nAIfqALw_I_EcA",
        "content_tag": "High Fantasy",
    },
    {
        "scenario_id": uuid.UUID("11111111-2222-3333-4444-555555555552"),
        "title": "Substratum 9",
        "logline": "A geothermal drill station goes dark beneath the Martian permafrost. You are the sole structural mechanic dispatched into the silence.",
        "mode": "master",
        "complexity_tier": "master",
        "player_count_support": "solo",
        "genre_tags": ["Sci-Fi"],
        "rating_avg": Decimal("4.80"),
        "play_count": 2150,
        "status": "published",
        "estimated_playtime": "1h 15m",
        "cover_image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuA4C2Yt59RYSPW_NeBBF0QmZ3BO-QmGODi8ip-bkvDikFmyXjMTqtc9sYrd7Zo0nVDfh6O8roDJ_Qbh__1grrpISEaqShbi9UiBNajl9TqQLDSJFukpLGk3ezB6tOVGxKvw_vbmRRhNJIERiS0BEnFGstcp_hpkg_zHzkMCQ4TIJDV9RUd7RCEywmjRLP4BZ4J-wFxBGagQN7jAUZmQqc7vdiZlxxYeb6bIsVZEiIEC6h6e2CzO0nnsYg",
        "content_tag": "Sci-Fi",
    },
    {
        "scenario_id": uuid.UUID("11111111-2222-3333-4444-555555555553"),
        "title": "The Grey Ledger",
        "logline": "The dockmaster's ledger had three names scratched out in fresh ink. Rain tapped against your trench coat as footsteps echoed from Pier 9.",
        "mode": "newbie",
        "complexity_tier": "newbie",
        "player_count_support": "solo",
        "genre_tags": ["Noir / Detective"],
        "rating_avg": Decimal("4.90"),
        "play_count": 1820,
        "status": "published",
        "estimated_playtime": "30m",
        "cover_image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuCaqmJks5pMWuWqfs1rjZMjAC_gfRkg2mNfRabJH3WuO2zAUUX0E4c3hDwM5AimoMVfTQq0ryrCZ4G066D790mswtyheJ1DDQT46pjZBFGMtWkSjgOVdqqhEf1Rrd9agr23pvocO-42OEPM96v6AIEjrd79wmlBNyJ-cO4rSrDHcq0xq5wttT-N9CBgp_oV00-dGqWNd2Y3JObPODJkXREO2l843spev_jTyY2Crln7nAIfqALw_I_EcA",
        "content_tag": "Noir / Detective",
    },
    {
        "scenario_id": uuid.UUID("11111111-2222-3333-4444-555555555554"),
        "title": "Echoes of Ash & Bone",
        "logline": "The kingdom fell three centuries ago, but the crypts beneath the palace refuse to keep their dead.",
        "mode": "master",
        "complexity_tier": "master",
        "player_count_support": "solo",
        "genre_tags": ["Dark Fantasy"],
        "rating_avg": Decimal("4.70"),
        "play_count": 940,
        "status": "published",
        "estimated_playtime": "1h 45m",
        "cover_image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuCaqmJks5pMWuWqfs1rjZMjAC_gfRkg2mNfRabJH3WuO2zAUUX0E4c3hDwM5AimoMVfTQq0ryrCZ4G066D790mswtyheJ1DDQT46pjZBFGMtWkSjgOVdqqhEf1Rrd9agr23pvocO-42OEPM96v6AIEjrd79wmlBNyJ-cO4rSrDHcq0xq5wttT-N9CBgp_oV00-dGqWNd2Y3JObPODJkXREO2l843spev_jTyY2Crln7nAIfqALw_I_EcA",
        "content_tag": "Dark Fantasy",
    },
    {
        "scenario_id": uuid.UUID("11111111-2222-3333-4444-555555555555"),
        "title": "Neon Drift 2088",
        "logline": "The courier run through Neo-Kowloon is straight down the central line. Only problem is the payload is burning through its containment vessel.",
        "mode": "newbie",
        "complexity_tier": "newbie",
        "player_count_support": "solo",
        "genre_tags": ["Cyberpunk"],
        "rating_avg": Decimal("4.80"),
        "play_count": 1420,
        "status": "published",
        "estimated_playtime": "50m",
        "cover_image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuA4C2Yt59RYSPW_NeBBF0QmZ3BO-QmGODi8ip-bkvDikFmyXjMTqtc9sYrd7Zo0nVDfh6O8roDJ_Qbh__1grrpISEaqShbi9UiBNajl9TqQLDSJFukpLGk3ezB6tOVGxKvw_vbmRRhNJIERiS0BEnFGstcp_hpkg_zHzkMCQ4TIJDV9RUd7RCEywmjRLP4BZ4J-wFxBGagQN7jAUZmQqc7vdiZlxxYeb6bIsVZEiIEC6h6e2CzO0nnsYg",
        "content_tag": "Cyberpunk",
    },
]


async def seed_scenarios_and_playthroughs():
    async with AsyncSessionFactory() as session:
        # 1. Verify creator exists
        user_res = await session.execute(select(User).where(User.user_id == CREATOR_ID))
        creator = user_res.scalar_one_or_none()
        if not creator:
            user_res = await session.execute(select(User).limit(1))
            creator = user_res.scalar_one_or_none()
            if not creator:
                raise RuntimeError("No user found to act as creator")
        creator_id = creator.user_id
        print(f"Using creator_id: {creator_id}")

        # 2. Upsert Scenarios
        for data in STITCH_SCENARIOS:
            sc_id = data["scenario_id"]
            existing = (
                await session.execute(
                    select(Scenario).where(Scenario.scenario_id == sc_id)
                )
            ).scalar_one_or_none()
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                existing.published_at = datetime.now(timezone.utc)
                print(f"Updated scenario: {data['title']}")
            else:
                scenario = Scenario(
                    creator_id=creator_id,
                    published_at=datetime.now(timezone.utc),
                    world_data={},
                    rules={},
                    **data,
                )
                session.add(scenario)
                print(f"Created scenario: {data['title']}")

        await session.flush()

        # 3. Seed Continue playthroughs for active users
        all_users = (await session.execute(select(User))).scalars().all()
        now = datetime.now(timezone.utc)

        for user_obj in all_users:
            u_id = user_obj.user_id

            # Playthrough 1: The Grey Ledger (Turn 14, 2h ago)
            gl_id = uuid.UUID("11111111-2222-3333-4444-555555555553")
            gl_pt_id = uuid.uuid5(u_id, "grey-ledger-stitch")
            existing_gl = (
                await session.execute(
                    select(Playthrough).where(Playthrough.playthrough_id == gl_pt_id)
                )
            ).scalar_one_or_none()

            gl_state = {
                "author": "M. E. Holloway",
                "excerpt": "The dockmaster's ledger had three names scratched out in fresh ink. Rain tapped against your trench coat as footsteps echoed from Pier 9.",
                "genre": "Noir / Detective",
            }
            if existing_gl:
                existing_gl.turn_count = 14
                existing_gl.status = "active"
                existing_gl.updated_at = now - timedelta(minutes=5)
                existing_gl.state = gl_state
            else:
                session.add(
                    Playthrough(
                        playthrough_id=gl_pt_id,
                        scenario_id=gl_id,
                        created_by=u_id,
                        turn_count=14,
                        status="active",
                        scenario_version=1,
                        scenario_snapshot={},
                        state=gl_state,
                        created_at=now - timedelta(days=2),
                        updated_at=now - timedelta(minutes=5),
                    )
                )

            # Playthrough 2: Substratum 9 (Turn 8, 1d ago)
            s9_id = uuid.UUID("11111111-2222-3333-4444-555555555552")
            s9_pt_id = uuid.uuid5(u_id, "substratum-9-stitch")
            existing_s9 = (
                await session.execute(
                    select(Playthrough).where(Playthrough.playthrough_id == s9_pt_id)
                )
            ).scalar_one_or_none()

            s9_state = {
                "author": "Vance Thorne",
                "excerpt": "Air pressure in Sector 4 dropped to 0.4 atm. The auxiliary geothermal valve responded, but thermal telemetry showed rising coolant levels.",
                "genre": "Sci-Fi",
            }
            if existing_s9:
                existing_s9.turn_count = 8
                existing_s9.status = "active"
                existing_s9.updated_at = now - timedelta(minutes=15)
                existing_s9.state = s9_state
            else:
                session.add(
                    Playthrough(
                        playthrough_id=s9_pt_id,
                        scenario_id=s9_id,
                        created_by=u_id,
                        turn_count=8,
                        status="active",
                        scenario_version=1,
                        scenario_snapshot={},
                        state=s9_state,
                        created_at=now - timedelta(days=4),
                        updated_at=now - timedelta(minutes=15),
                    )
                )

        await session.commit()
        print("Successfully seeded Stitch scenarios and playthroughs!")


if __name__ == "__main__":
    asyncio.run(seed_scenarios_and_playthroughs())
