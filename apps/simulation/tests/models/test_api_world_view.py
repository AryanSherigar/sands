from typing import get_args, get_origin, get_type_hints
from uuid import UUID

from app.models.api_world_view import (
    IntRange,
    OwnFactionView,
    RegionView,
    RivalView,
    SceneRef,
    Visibility,
    WorldView,
)
from app.models.world_character import LeaderState, PlayerBeliefs
from app.models.world_clock import RngState, TurnClock
from app.models.world_diplomacy import OutrageState
from app.models.world_faction import StanceState
from app.models.world_player import PlayerRuler
from app.models.world_pressure import (
    HopeReading,
    MediationOffer,
    PressureState,
    ShockRecord,
    StrainReading,
    SubsidyState,
    WillReading,
)
from pydantic import BaseModel
from strategy_contracts.enums import RelationStatus, TaxRate, Terrain
from strategy_contracts.scene import SceneType

from tests.models.builders import make_region

RIVAL_VIEW_ALLOWLIST = {
    "faction_id",
    "name",
    "leader_name",
    "relation",
    "treasury_range",
    "manpower_range",
}
SECRET_TYPES = {
    StanceState,
    PlayerBeliefs,
    OutrageState,
    RngState,
    LeaderState,
    PressureState,
    ShockRecord,
    MediationOffer,
    SubsidyState,
    HopeReading,
    WillReading,
    StrainReading,
}


def _reachable_models(annotation: object, seen: set[type]) -> None:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if annotation in seen:
            return
        seen.add(annotation)
        for hint in get_type_hints(annotation).values():
            _reachable_models(hint, seen)
        return
    if get_origin(annotation) is not None:
        for argument in get_args(annotation):
            _reachable_models(argument, seen)


def _world_view() -> WorldView:
    return WorldView(
        clock=TurnClock(turn=1, start_year=1000, start_month=3),
        my_faction=OwnFactionView(
            id="house_carrow",
            leader_id="valdren",
            treasury=100,
            manpower=200,
            stability=65,
            war_exhaustion=0,
            reputation=0,
            tax_rate=TaxRate.NORMAL,
        ),
        ruler=PlayerRuler(
            name="Valdren",
            trait_ids=["honorable", "cautious"],
            ambition_ids=["ambition_peace"],
        ),
        regions=[
            RegionView(
                region_id="ashford",
                owner_id="house_ashford",
                terrain=Terrain.PLAIN,
                visibility=Visibility.FOGGED,
                last_seen_turn=0,
                garrison_estimate=IntRange(low=10, high=40),
            ),
            RegionView(
                region_id="carrow_vale",
                owner_id="house_carrow",
                terrain=Terrain.HILLS,
                visibility=Visibility.VISIBLE,
                detail=make_region("carrow_vale", "house_carrow"),
            ),
        ],
        rivals=[
            RivalView(
                faction_id="house_ashford",
                name="House Ashford",
                leader_name="Mira",
                relation=RelationStatus.PEACE,
                treasury_range=IntRange(low=50, high=150),
                manpower_range=IntRange(low=100, high=300),
            )
        ],
        orders_remaining=6,
        pending_scene=SceneRef(
            scene_id=UUID("11111111-1111-1111-1111-111111111111"),
            scene_type=SceneType.NEGOTIATION,
        ),
    )


def test_rival_view_exposes_only_allowlisted_fields() -> None:
    assert set(RivalView.model_fields) == RIVAL_VIEW_ALLOWLIST


def test_region_detail_defaults_to_none() -> None:
    region = RegionView(
        region_id="ashford",
        owner_id=None,
        terrain=Terrain.PLAIN,
        visibility=Visibility.FOGGED,
    )
    assert region.detail is None


def test_world_view_reaches_no_secret_model() -> None:
    reachable: set[type] = set()
    _reachable_models(WorldView, reachable)
    assert reachable.isdisjoint(SECRET_TYPES)


def test_world_view_round_trips() -> None:
    view = _world_view()
    assert WorldView.model_validate_json(view.model_dump_json()) == view
