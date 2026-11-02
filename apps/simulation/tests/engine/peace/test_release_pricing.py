from app.engine.peace.pricing import CardPrice, price_card
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType
from strategy_contracts.terms import ReleasePrisonersTerm, TermsCard

from tests.engine.diplomacy.builders import set_traits
from tests.engine.peace.builders import PLAYER, SCENARIO, WRATHFUL_RIVAL, make_world

HOLDER = PLAYER
ORIGIN = WRATHFUL_RIVAL
TUNING = SCENARIO.tuning.peace


def _troops(world, count: int, prisoner_id: str = "prisoner_1") -> str:
    world.prisoners.append(
        PrisonerState(
            id=prisoner_id,
            held_by_id=HOLDER,
            origin_faction_id=ORIGIN,
            kind=PrisonerKind.TROOPS,
            troop_count=count,
            origin_battle_id="battle_1",
            troops_by_type={TroopType.INFANTRY: count},
        )
    )
    return prisoner_id


def _noble(world, character_id: str, prisoner_id: str) -> str:
    world.prisoners.append(
        PrisonerState(
            id=prisoner_id,
            held_by_id=HOLDER,
            origin_faction_id=ORIGIN,
            kind=PrisonerKind.CHARACTER,
            character_id=character_id,
        )
    )
    return prisoner_id


def _card(prisoner_ids: list[str], ransom_gold: int = 0) -> TermsCard:
    term = ReleasePrisonersTerm(
        holder_id=HOLDER,
        recipient_id=ORIGIN,
        prisoner_ids=prisoner_ids,
        ransom_gold=ransom_gold,
    )
    return TermsCard(proposer_id=HOLDER, counterpart_id=ORIGIN, terms=[term])


def _given(world, prisoner_ids: list[str], signer: str = HOLDER) -> int:
    return price_card(SCENARIO, _card(prisoner_ids), signer, world).concession


def _calm_world():
    world = make_world()
    world.factions[ORIGIN].stability = 100
    set_traits(world, ORIGIN, ["pragmatic"])
    return world


def test_a_handful_of_released_troops_is_worth_almost_nothing() -> None:
    world = _calm_world()

    assert _given(world, [_troops(world, 5)]) == 0


def test_a_big_release_counts_for_much_more_than_a_small_one() -> None:
    small, large = _calm_world(), _calm_world()

    assert _given(large, [_troops(large, 2000)]) > _given(small, [_troops(small, 200)])


def test_ten_times_the_troops_is_far_less_than_ten_times_the_value() -> None:
    thousand, ten_thousand = _calm_world(), _calm_world()

    low = _given(thousand, [_troops(thousand, 1000)])
    high = _given(ten_thousand, [_troops(ten_thousand, 10000)])

    assert high > low
    assert high < 3 * low


def test_a_huge_release_cannot_outgrow_its_ceiling() -> None:
    world = _calm_world()
    ceiling = TUNING.release_troop_ceiling * TUNING.release_want_max_percent // 100

    assert _given(world, [_troops(world, 5_000_000)]) <= ceiling


def test_a_ruler_is_worth_more_than_a_noble_and_a_noble_more_than_a_squad() -> None:
    world = _calm_world()
    ruler = _noble(world, world.factions[ORIGIN].leader_id, "prisoner_ruler")
    noble = _noble(world, "someone_else", "prisoner_noble")
    squad = _troops(world, 100, "prisoner_squad")

    ruler_value = _given(world, [ruler])
    noble_value = _given(world, [noble])
    squad_value = _given(world, [squad])

    assert ruler_value > noble_value > squad_value


def test_a_desperate_realm_values_its_people_more() -> None:
    calm, desperate = _calm_world(), _calm_world()
    desperate.factions[ORIGIN].stability = 0
    for world in (calm, desperate):
        _noble(world, "someone_else", "prisoner_noble")

    assert _given(desperate, ["prisoner_noble"]) > _given(calm, ["prisoner_noble"])


def test_the_signer_who_receives_the_prisoners_pays_the_value_as_demand() -> None:
    world = _calm_world()
    ids = [_noble(world, "someone_else", "prisoner_noble")]

    price = price_card(SCENARIO, _card(ids), ORIGIN, world)

    assert price.demand > 0
    assert price.concession == 0


def test_ransom_gold_counts_as_what_the_holder_gains() -> None:
    world = _calm_world()
    ids = [_noble(world, "someone_else", "prisoner_noble")]
    gold = 10 * TUNING.gold_per_score_point

    without = price_card(SCENARIO, _card(ids), HOLDER, world)
    paid = price_card(SCENARIO, _card(ids, gold), HOLDER, world)

    assert paid.demand == without.demand + 10


def test_the_legacy_ruleset_keeps_the_flat_value_per_prisoner() -> None:
    world = _calm_world()
    world.peace_ruleset = 1
    ids = [_troops(world, 5000, "prisoner_a"), _troops(world, 5, "prisoner_b")]

    price = price_card(SCENARIO, _card(ids), HOLDER, world)

    assert price == CardPrice(demand=0, concession=2 * TUNING.prisoner_score_value)


def test_without_a_world_the_flat_value_applies() -> None:
    price = price_card(
        SCENARIO, _card(["prisoner_a", "prisoner_b", "prisoner_c"]), HOLDER
    )

    assert price.concession == 3 * TUNING.prisoner_score_value
