import pytest
from app.engine.alliances.denounce import expire_alliances
from app.engine.alliances.joining import join_war
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.peace.signing import sign_peace
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import CommitmentStatus, WarState
from app.models.world_state import WorldState
from strategy_contracts.alliance import AllianceType
from strategy_contracts.enums import RelationStatus

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    SCENE_ID,
    WRATHFUL_RIVAL,
    add_alliance,
    make_party_card,
    make_world,
)

DIPLOMACY = SCENARIO.tuning.diplomacy
ALLIANCE_TURNS = 4


def _joined_war() -> tuple[WorldState, WarState]:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    join_war(world, SCENARIO, world.alliance.calls.pop())
    return world, world.wars[0]


def _status(world: WorldState, first: str, second: str) -> RelationStatus:
    pair = tuple(sorted((first, second)))
    return next(
        item.status
        for item in world.relations
        if (item.faction_a, item.faction_b) == pair
    )


def _truce_pairs(world: WorldState) -> list[tuple[str, str]]:
    return sorted((truce.faction_a, truce.faction_b) for truce in world.truces)


def test_principals_only_peace_leaves_unnamed_ally_at_war() -> None:
    world, war = _joined_war()

    sign_peace(world, SCENARIO, make_party_card(WRATHFUL_RIVAL, PLAYER), SCENE_ID)

    assert world.wars == [war]
    assert _status(world, WRATHFUL_RIVAL, PLAYER) == RelationStatus.PEACE
    assert _status(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL) == RelationStatus.WAR
    assert _truce_pairs(world) == [tuple(sorted((PLAYER, WRATHFUL_RIVAL)))]


def test_all_parties_named_ends_war_and_creates_truce_per_opposing_pair() -> None:
    world, _ = _joined_war()
    card = make_party_card(WRATHFUL_RIVAL, PLAYER, [CAUTIOUS_RIVAL])

    sign_peace(world, SCENARIO, card, SCENE_ID)

    assert world.wars == []
    assert _status(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL) == RelationStatus.PEACE
    assert _truce_pairs(world) == sorted(
        [
            tuple(sorted((PLAYER, WRATHFUL_RIVAL))),
            tuple(sorted((CAUTIOUS_RIVAL, WRATHFUL_RIVAL))),
        ]
    )


def test_unnamed_allys_score_and_goals_survive() -> None:
    world, war = _joined_war()
    war.war_score_attacker, war.war_score_defender = 20, 10
    goals_before = list(war.goals)

    sign_peace(world, SCENARIO, make_party_card(WRATHFUL_RIVAL, PLAYER), SCENE_ID)

    assert CAUTIOUS_RIVAL in war.participant_ids
    assert (war.war_score_attacker, war.war_score_defender) == (20, 10)
    assert war.goals == goals_before


def test_final_signing_naming_the_remaining_parties_ends_the_war() -> None:
    world, _ = _joined_war()
    sign_peace(world, SCENARIO, make_party_card(WRATHFUL_RIVAL, PLAYER), SCENE_ID)

    sign_peace(
        world,
        SCENARIO,
        make_party_card(CAUTIOUS_RIVAL, WRATHFUL_RIVAL, [PLAYER]),
        SCENE_ID,
    )

    assert world.wars == []
    assert len(world.truces) == 2


def test_double_sign_fails_and_changes_nothing() -> None:
    world, _ = _joined_war()
    card = make_party_card(WRATHFUL_RIVAL, PLAYER)
    sign_peace(world, SCENARIO, card, SCENE_ID)
    truces = list(world.truces)

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "no_war"
    assert world.truces == truces


def test_named_party_outside_the_war_is_rejected() -> None:
    world = make_world()
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    card = make_party_card(WRATHFUL_RIVAL, PLAYER, [CAUTIOUS_RIVAL])

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "invalid_term"
    assert len(world.wars) == 1


def test_two_party_war_still_ends_on_one_signing() -> None:
    world = make_world()
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )

    sign_peace(world, SCENARIO, make_party_card(WRATHFUL_RIVAL, PLAYER), SCENE_ID)

    assert world.wars == []
    assert _status(world, WRATHFUL_RIVAL, PLAYER) == RelationStatus.PEACE


def _offensive_ally_war(is_banned: bool) -> tuple[WorldState, WarState]:
    world = make_world()
    add_alliance(
        world,
        WRATHFUL_RIVAL,
        CAUTIOUS_RIVAL,
        AllianceType.OFFENSIVE,
        is_separate_peace_banned=is_banned,
    )
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    join_war(world, SCENARIO, world.alliance.calls.pop())
    return world, world.wars[0]


def test_ally_separate_peace_allowed_without_clause() -> None:
    world, war = _offensive_ally_war(is_banned=False)

    sign_peace(world, SCENARIO, make_party_card(CAUTIOUS_RIVAL, PLAYER), SCENE_ID)

    assert world.wars == [war]
    assert _status(world, CAUTIOUS_RIVAL, PLAYER) == RelationStatus.PEACE
    assert world.oathbreakers == []


def test_ally_separate_peace_with_clause_breaches_once() -> None:
    world, _ = _offensive_ally_war(is_banned=True)
    alliance = world.commitments[0]
    reputation = world.factions[CAUTIOUS_RIVAL].reputation

    sign_peace(world, SCENARIO, make_party_card(CAUTIOUS_RIVAL, PLAYER), SCENE_ID)

    assert alliance.status is CommitmentStatus.BREACHED
    assert [mark.faction_id for mark in world.oathbreakers] == [CAUTIOUS_RIVAL]
    assert reputation - world.factions[CAUTIOUS_RIVAL].reputation == (
        DIPLOMACY.breach_reputation_cost
    )


def test_ally_signing_with_its_partner_named_does_not_breach() -> None:
    world, _ = _offensive_ally_war(is_banned=True)

    sign_peace(
        world,
        SCENARIO,
        make_party_card(CAUTIOUS_RIVAL, PLAYER, [WRATHFUL_RIVAL]),
        SCENE_ID,
    )

    assert world.oathbreakers == []
    assert world.wars == []


def test_fixed_duration_alliance_expiring_mid_war_keeps_ally_in_war() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL, duration_turns=ALLIANCE_TURNS)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    join_war(world, SCENARIO, world.alliance.calls.pop())
    world.clock.turn += ALLIANCE_TURNS

    expire_alliances(world)

    assert CAUTIOUS_RIVAL in world.wars[0].participant_ids
    assert _status(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL) == RelationStatus.WAR
