from app.engine.alliances.answers import apply_answer, resolve_calls
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.hashing import canonical_world_json, world_hash
from app.engine.peace.signing import sign_peace
from app.models.orders import AnswerCallOrder, DeclareWarOrder
from app.models.world_alliance import AllianceStanding
from app.models.world_state import WorldState
from strategy_contracts.alliance import AllianceType

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
from tests.engine.diplomacy.builders import set_traits


def _scripted_war() -> WorldState:
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, ["honorable", "trusting"])
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL, is_separate_peace_banned=True)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )
    world.clock.turn = world.alliance.calls[0].deadline_turn
    resolve_calls(world, SCENARIO)
    sign_peace(world, SCENARIO, make_party_card(WRATHFUL_RIVAL, PLAYER), SCENE_ID)
    world.clock.turn += 1
    sign_peace(
        world,
        SCENARIO,
        make_party_card(CAUTIOUS_RIVAL, WRATHFUL_RIVAL, [PLAYER]),
        SCENE_ID,
    )
    return world


def test_scripted_war_with_call_join_and_staged_peace_replays_identically() -> None:
    first, second = _scripted_war(), _scripted_war()

    assert world_hash(first) == world_hash(second)
    assert first.wars == []
    assert len(first.truces) == 2


def test_alliance_state_survives_a_document_round_trip() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL, AllianceType.OFFENSIVE)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=PLAYER, target_faction_id=WRATHFUL_RIVAL),
    )
    world.alliance.standing.append(
        AllianceStanding(alliance_id="commitment_1", refusals_by_faction={"aa": 1})
    )

    restored = WorldState.model_validate(world.model_dump(mode="json"))

    assert world_hash(restored) == world_hash(world)
    assert restored.alliance == world.alliance
    assert restored.wars == world.wars


def test_legacy_ruleset_world_hash_ignores_alliance_fields() -> None:
    legacy = make_world()
    legacy.alliance_ruleset = 0
    other = legacy.model_copy(deep=True)
    other.alliance.standing.append(AllianceStanding(alliance_id="commitment_1"))

    text = canonical_world_json(legacy)
    assert '"alliance":' not in text
    assert "alliance_ruleset" not in text
    assert world_hash(legacy) == world_hash(other)


def test_player_answer_is_part_of_the_hash() -> None:
    joined = make_world()
    refused = make_world()
    for world in (joined, refused):
        add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
        declare_war(
            world,
            SCENARIO,
            DeclareWarOrder(
                faction_id=WRATHFUL_RIVAL, target_faction_id=CAUTIOUS_RIVAL
            ),
        )
    for world, is_joining in ((joined, True), (refused, False)):
        order = AnswerCallOrder(
            faction_id=PLAYER, call_id=world.alliance.calls[0].id, is_joining=is_joining
        )
        apply_answer(world, SCENARIO, order)

    assert world_hash(joined) != world_hash(refused)
