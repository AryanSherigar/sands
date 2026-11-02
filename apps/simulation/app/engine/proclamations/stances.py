from typing import Literal

from app.models.world_state import WorldState
from strategy_contracts.proclamation import (
    EstatePillar,
    ProclamationDomain,
    ProclamationDraft,
    ProclamationMinisterView,
)

MINISTER_TITLES: dict[EstatePillar, str] = {
    EstatePillar.NOBILITY: "Lord Chancellor Morvath",
    EstatePillar.MILITARY: "High Marshal Vane",
    EstatePillar.BURGHERS: "Lord Treasurer Hest",
    EstatePillar.CLERGY: "Arch-Prelate Tomas",
}

ESTATE_GRIEVANCES: dict[EstatePillar, str] = {
    EstatePillar.NOBILITY: "Ancient feudal privileges and baronial land charters.",
    EstatePillar.MILITARY: "Troop readiness, rations, and battlefield command.",
    EstatePillar.BURGHERS: "Merchant solvency, trade tariffs, and coinage debasement.",
    EstatePillar.CLERGY: "Church tithes, holy sanctuaries, and canon law.",
}


def _score_minister_alignment(
    estate: EstatePillar,
    draft: ProclamationDraft,
    is_at_war: bool,
    treasury_gold: int,
) -> int:
    score = 0
    if draft.domain == ProclamationDomain.MARTIAL_LEVIES:
        score += 35 if estate is EstatePillar.MILITARY else -15
    elif draft.domain == ProclamationDomain.EMERGENCY_TAXATION:
        score += -40 if estate is EstatePillar.BURGHERS else 10
    elif draft.domain == ProclamationDomain.RELIGIOUS_ORTHODOXY:
        score += 45 if estate is EstatePillar.CLERGY else -20
    elif draft.domain == ProclamationDomain.NOBLE_PRIVILEGES:
        score += 40 if estate is EstatePillar.NOBILITY else -10
    elif draft.domain == ProclamationDomain.POPULAR_RELIEF:
        score += -25 if estate is EstatePillar.NOBILITY else 10

    if is_at_war and estate is EstatePillar.MILITARY:
        score += 25
    if treasury_gold < 100 and estate is EstatePillar.BURGHERS:
        score -= 20
    if draft.concession_estate == estate:
        score += 30
    return score


def _map_score_to_stance(score: int) -> Literal["support", "cautious", "oppose"]:
    if score >= 15:
        return "support"
    if score <= -15:
        return "oppose"
    return "cautious"


def evaluate_minister_stances(
    world: WorldState, draft: ProclamationDraft
) -> list[ProclamationMinisterView]:
    player_id = next((k for k, f in world.factions.items() if f.is_player), None)
    is_at_war = any(
        w.attacker_id == player_id or w.defender_id == player_id for w in world.wars
    )
    faction = world.factions.get(player_id) if player_id else None
    treasury_gold = faction.treasury if faction is not None else 100

    ministers: list[ProclamationMinisterView] = []
    for estate in (
        EstatePillar.NOBILITY,
        EstatePillar.MILITARY,
        EstatePillar.BURGHERS,
        EstatePillar.CLERGY,
    ):
        score = _score_minister_alignment(estate, draft, is_at_war, treasury_gold)
        stance = _map_score_to_stance(score)
        ministers.append(
            ProclamationMinisterView(
                estate=estate,
                title=MINISTER_TITLES[estate],
                stance=stance,
                primary_grievance=ESTATE_GRIEVANCES[estate],
            )
        )
    return ministers
