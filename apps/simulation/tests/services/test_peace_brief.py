from app.services.peace_brief import STANDING_MARGIN, build_peace_brief
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scene import WarStanding
from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
    set_score,
)


def _brief(attacker: int, defender: int):
    # NOTE: in this world the player is the defender.
    world = make_world()
    war = set_score(add_war(world), attacker=attacker, defender=defender)
    return build_peace_brief(world, SCENARIO, PLAYER, WRATHFUL_RIVAL, war)


def test_the_brief_names_both_factions_with_their_ids() -> None:
    brief = _brief(0, 0)

    assert (brief.player_faction_id, brief.counterpart_faction_id) == (
        PLAYER,
        WRATHFUL_RIVAL,
    )
    assert brief.player_faction_name and brief.counterpart_faction_name


def test_standing_is_the_counterparts_view_of_the_score_edge() -> None:
    assert _brief(0, STANDING_MARGIN).standing is WarStanding.TRAILING
    assert _brief(STANDING_MARGIN, 0).standing is WarStanding.LEADING
    assert _brief(0, STANDING_MARGIN - 1).standing is WarStanding.EVEN


def test_the_brief_lists_every_tier_with_its_guarantor_rule() -> None:
    brief = _brief(0, 0)

    by_tier = {item.tier: item for item in brief.tiers}
    assert set(by_tier) == set(PeaceTier)
    assert not by_tier[PeaceTier.SHORT].needs_guarantor
    assert by_tier[PeaceTier.GENERATION].needs_guarantor


def test_cession_candidates_are_each_sides_own_regions_in_id_order() -> None:
    brief = _brief(0, 0)

    ids = [item.region_id for item in brief.player_regions]
    assert ids == sorted(ids)
    assert all(item.name for item in brief.counterpart_regions)


def test_the_brief_carries_no_score_or_threshold_numbers() -> None:
    dumped = _brief(40, 5).model_dump_json()

    assert "accept_at" not in dumped
    assert "score" not in dumped
