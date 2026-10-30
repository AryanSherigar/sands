from strategy_contracts.enums import Terrain
from strategy_contracts.map import MapDocument, MapRegion, Point

SQUARE_OUTLINE = "M0 0 L10 0 L10 10 L0 10 Z"


def make_region(region_id: str, neighbor_ids: list[str]) -> MapRegion:
    return MapRegion(
        id=region_id,
        name=region_id.title(),
        terrain=Terrain.PLAIN,
        outline=SQUARE_OUTLINE,
        label_point=Point(x=5, y=5),
        neighbor_ids=neighbor_ids,
    )


def make_map(links: dict[str, list[str]]) -> MapDocument:
    return MapDocument(
        width=100,
        height=100,
        regions=[make_region(region_id, ids) for region_id, ids in links.items()],
    )


def make_terms_card(term: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "proposer_id": "house_carrow",
        "counterpart_id": "house_ashford",
        "terms": [
            term
            or {
                "kind": "tribute",
                "payer_id": "house_ashford",
                "payee_id": "house_carrow",
                "gold_per_turn": 5,
                "duration_turns": 6,
            }
        ],
    }


def make_negotiation_package(**overrides: object) -> dict[str, object]:
    package: dict[str, object] = {
        "scene_id": "11111111-1111-1111-1111-111111111111",
        "playthrough_id": "22222222-2222-2222-2222-222222222222",
        "scene_type": "negotiation",
        "turn": 3,
        "situation": {"summary": "Ashford sues for peace.", "facts": []},
        "hidden_limits": {"acceptance": {"accept_at": 10, "haggle_at": 4}},
        "allowed_outcomes": [
            {
                "kind": "terms_card",
                "allowed_term_kinds": ["tribute", "non_aggression"],
                "price_by_term_kind": {"tribute": 3},
                "war_score_available": 12,
            }
        ],
        "exchange_cap": 6,
        "default_outcome": {"kind": "terms_card", "result": "refused"},
    }
    package.update(overrides)
    return package
