from httpx import AsyncClient
from strategy_contracts.examples import load_three_crowns_expanded
from tests.services.test_campaign_service import initialization

HEADERS = {"X-Internal-Service-Token": "internal"}
PLAYER = "house_ashford"
ENEMY = "house_carrow"
TARGET_REGION = "carrow_vale"
ARMY_IDS = ("army_ashford_1", "army_ashford_2")
CONQUEST_KINDS = (
    "siege_started",
    "siege_progressed",
    "region_occupied",
    "region_conquered",
    "occupation_lifted",
)
MAX_TURNS = 14


class Game:
    def __init__(self, api: AsyncClient) -> None:
        self.api = api
        self.base = ""
        self.world: dict = {}
        self.operations = 0

    async def start(self) -> None:
        scenario = load_three_crowns_expanded()
        next(item for item in scenario.factions if item.id == PLAYER).is_playable = True
        request = initialization().model_copy(
            update={"player_faction_id": PLAYER, "scenario": scenario}
        )
        payload = request.model_dump(mode="json")
        await self.api.post("/internal/v1/playthroughs", json=payload, headers=HEADERS)
        self.base = f"/v1/playthroughs/{payload['playthrough_id']}"
        await self.refresh()

    async def refresh(self) -> None:
        self.world = (await self.api.get(f"{self.base}/world")).json()

    def guard(self, is_battle_window: bool = False) -> dict[str, object]:
        self.operations += 1
        return {
            "operation_id": f"op{self.operations}",
            "expected_world_version": self.world["world_version"],
            "expected_turn": self.world["turn"],
            "expected_wave": self.world["wave"] + (1 if is_battle_window else 0),
        }

    async def order(self, command: dict[str, object]) -> int:
        response = await self.api.post(
            f"{self.base}/commands", json=self.guard() | {"command": command}
        )
        await self.refresh()
        return response.status_code

    async def settle_battles(self) -> None:
        for battle in self.world["battles"]:
            if "delegate_battle" not in battle.get("legal_commands", []):
                continue
            command = {
                "kind": "delegate_battle",
                "faction_id": PLAYER,
                "battle_id": battle["id"],
            }
            response = await self.api.post(
                f"{self.base}/commands",
                json=self.guard(is_battle_window=True) | {"command": command},
            )
            assert response.status_code == 200
            await self.refresh()
        advanced = await self.api.post(
            f"{self.base}/battles/advance", json=self.guard(is_battle_window=True)
        )
        assert advanced.status_code == 200

    async def decline_scene(self) -> None:
        scene_id = self.world["scene_id"]
        response = await self.api.post(
            f"{self.base}/scenes/{scene_id}/decision",
            json=self.guard() | {"is_confirmed": False},
        )
        assert response.status_code == 200

    async def end_turn(self) -> None:
        start_turn = self.world["turn"]
        response = await self.api.post(f"{self.base}/end-turn", json=self.guard())
        assert response.status_code == 200
        for _ in range(MAX_TURNS):
            await self.refresh()
            status = self.world["status"]
            if status == "planning" and self.world["turn"] > start_turn:
                return
            if status == "awaiting_scene":
                await self.decline_scene()
            else:
                await self.settle_battles()
        raise AssertionError("the turn never returned to planning")

    def region(self, region_id: str) -> dict:
        return next(
            item for item in self.world["regions"] if item["region_id"] == region_id
        )

    async def conquest_kinds(self, turn: int) -> list[str]:
        report = (await self.api.get(f"{self.base}/turns/{turn}/report")).json()
        return [
            line["kind"] for line in report["lines"] if line["kind"] in CONQUEST_KINDS
        ]


async def test_a_war_is_won_on_the_field_by_taking_a_region(api: AsyncClient) -> None:
    game = Game(api)
    await game.start()
    assert (
        await game.order(
            {"kind": "declare_war", "faction_id": PLAYER, "target_faction_id": ENEMY}
        )
        == 200
    )
    await game.end_turn()
    pairs = [(war["attacker_id"], war["defender_id"]) for war in game.world["wars"]]
    assert (PLAYER, ENEMY) in pairs
    for army_id in ARMY_IDS:
        order = {
            "kind": "attack",
            "faction_id": PLAYER,
            "army_id": army_id,
            "target_region_id": TARGET_REGION,
        }
        assert await game.order(order) == 200

    seen: list[str] = []
    for _ in range(MAX_TURNS):
        turn = game.world["turn"]
        await game.end_turn()
        seen += await game.conquest_kinds(turn)
        if game.region(TARGET_REGION)["owner_id"] == PLAYER:
            break

    assert game.region(TARGET_REGION)["owner_id"] == PLAYER
    assert game.region(TARGET_REGION).get("occupation") is None
    assert seen[0] == "siege_started"
    assert seen.index("region_occupied") < seen.index("region_conquered")
