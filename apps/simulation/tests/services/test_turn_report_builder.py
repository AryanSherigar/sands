from app.engine.diplomacy.events import diplomacy_event
from app.engine.sieges.events import region_conquered, siege_started
from app.models.world_battle import (
    BattleOutcome,
    BattleSide,
    ExchangeReceipt,
    LossAccounting,
)
from app.models.world_character import GovernorState
from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange
from app.services.turn_report_builder import build_event_lines, build_turn_report
from strategy_contracts.enums import TroopType
from tests.engine.battles.builders import (
    ATTACKER,
    BATTLE_ID,
    DEFENDER,
    REGION,
    battle_fixture,
    start_battle,
)
from tests.engine.diplomacy.builders import make_world
from tests.engine.sieges.builders import (
    BESIEGER,
    BESIEGER_ARMY,
    TARGET_OWNER,
    TARGET_REGION,
    make_siege_world,
)


def _event(
    seq: int,
    kind: str,
    subjects: list[str],
    changes: list[StateChange] | None = None,
    inputs: dict[str, int] | None = None,
    is_major: bool = False,
) -> EventLogEntry:
    return EventLogEntry(
        seq=seq,
        turn=3,
        phase=PhaseName.ECONOMY,
        kind=kind,
        is_major=is_major,
        cause=EventCause(summary_key=kind, subject_ids=subjects, inputs=inputs or {}),
        changes=changes or [],
    )


def _treasury(faction: str, before: int, after: int) -> list[StateChange]:
    return [
        StateChange(path=f"factions.{faction}.treasury", before=before, after=after)
    ]


def _receipt(exchange_index: int, outcome: BattleOutcome | None) -> ExchangeReceipt:
    return ExchangeReceipt(
        battle_id=BATTLE_ID,
        campaign_turn=3,
        exchange_index=exchange_index,
        total_exchange=exchange_index,
        input_hash="in",
        output_hash="out",
        rule_version="1",
        outcome=outcome,
        accounting=[
            LossAccounting(
                army_id="army_a",
                before={TroopType.INFANTRY: 1000},
                survivors={TroopType.INFANTRY: 900},
                combat_losses={TroopType.INFANTRY: 80},
                pursuit_losses={TroopType.INFANTRY: 20},
            ),
            LossAccounting(
                army_id="army_b",
                before={TroopType.INFANTRY: 1000},
                survivors={TroopType.INFANTRY: 500},
                combat_losses={TroopType.INFANTRY: 500},
            ),
        ],
    )


def _world():
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    return world


def test_economy_lines_use_only_the_players_treasury_changes() -> None:
    events = [
        _event(1, "income_collected", [ATTACKER], _treasury(ATTACKER, 100, 160)),
        _event(2, "upkeep_paid", [ATTACKER], _treasury(ATTACKER, 160, 130)),
        _event(3, "income_collected", [DEFENDER], _treasury(DEFENDER, 50, 400)),
        _event(4, "army_raised", [ATTACKER], _treasury(ATTACKER, 130, 110)),
    ]
    report = build_turn_report(3, events, [], _world(), ATTACKER)
    assert [(line.category, line.amount) for line in report.economy] == [
        ("tax", 60),
        ("upkeep", -30),
        ("other", -20),
    ]
    assert report.net_gold == 10


def test_event_lines_hide_events_about_other_factions() -> None:
    events = [
        _event(1, "tax_rate_set", [ATTACKER]),
        _event(2, "tax_rate_set", [DEFENDER]),
        _event(3, "enemy_region_entered", ["army_b", REGION]),
        _event(4, "battle_army_accounted", [BATTLE_ID, "army_a"]),
    ]
    report = build_turn_report(3, events, [], _world(), ATTACKER)
    assert [line.kind for line in report.lines] == ["tax_rate_set"]


def test_major_event_kinds_ignore_events_the_player_cannot_see() -> None:
    events = [
        _event(1, "faction_defaulted", [DEFENDER], is_major=True),
        _event(2, "loan_overdue", [ATTACKER], is_major=True),
    ]
    report = build_turn_report(3, events, [], _world(), ATTACKER)
    assert report.major_event_kinds == ["loan_overdue"]


def test_battle_report_sums_only_own_losses_and_takes_final_outcome() -> None:
    receipts = [_receipt(1, None), _receipt(2, BattleOutcome.ATTACKER_VICTORY)]
    report = build_turn_report(3, [], receipts, _world(), ATTACKER)
    battle = report.battles[0]
    assert battle.region_id == REGION
    assert battle.own_side is BattleSide.ATTACKER
    assert battle.outcome is BattleOutcome.ATTACKER_VICTORY
    assert battle.exchanges == 2
    assert battle.own_losses == {TroopType.INFANTRY: 200}
    assert [(item.total_exchange, item.own_losses) for item in battle.rounds] == [
        (1, 100),
        (2, 100),
    ]


def test_battles_without_a_player_contingent_are_omitted() -> None:
    report = build_turn_report(3, [], [_receipt(1, None)], _world(), "house_zzz")
    assert report.battles == []


def test_event_lines_include_the_players_own_governors_and_not_rivals() -> None:
    world = _world()
    own_region = next(r.id for r in world.regions.values() if r.owner_id == ATTACKER)
    rival_region = next(r.id for r in world.regions.values() if r.owner_id == DEFENDER)
    world.governors["gov_own"] = GovernorState(
        id="gov_own", name="Own", region_id=own_region
    )
    world.governors["gov_rival"] = GovernorState(
        id="gov_rival", name="Rival", region_id=rival_region
    )
    events = [
        _event(1, "event_fired", ["gov_own"]),
        _event(2, "event_fired", ["gov_rival"]),
    ]
    report = build_turn_report(3, events, [], world, ATTACKER)
    assert [line.subject_ids for line in report.lines] == [["gov_own"]]


def test_ai_reason_events_never_appear_in_the_player_turn_report() -> None:
    from tests.engine.diplomacy.builders import CAUTIOUS_RIVAL, PLAYER, make_world

    world = make_world()
    planned = _event(1, "ai_order_planned", [CAUTIOUS_RIVAL], inputs={"score": 19})
    rejected = _event(2, "ai_order_rejected", [CAUTIOUS_RIVAL])
    aimed = _event(3, "ai_aim_set", [CAUTIOUS_RIVAL, PLAYER], inputs={"score": 9})

    report = build_turn_report(3, [planned, rejected, aimed], [], world, PLAYER)

    assert report.lines == []
    assert report.economy == []
    assert report.major_event_kinds == []


def test_player_turn_report_hides_a_rivals_bribe_of_the_players_envoy() -> None:
    world = make_world()
    event = diplomacy_event("envoy_bribed", ["house_dunwick"])

    assert build_event_lines([event], world, "house_ashford") == []


def test_conquest_reaches_the_besiegers_turn_report() -> None:
    world = make_siege_world()
    events = [region_conquered(BESIEGER, TARGET_OWNER, TARGET_REGION)]

    report = build_turn_report(3, events, [], world, BESIEGER)

    assert [line.kind for line in report.lines] == ["region_conquered"]
    assert report.major_event_kinds == ["region_conquered"]


def test_the_defender_sees_a_siege_on_its_own_region() -> None:
    world = make_siege_world()
    events = [siege_started(BESIEGER, TARGET_REGION, [BESIEGER_ARMY])]

    lines = build_event_lines(events, world, TARGET_OWNER)

    assert [line.kind for line in lines] == ["siege_started"]


def test_an_unrelated_faction_does_not_see_a_siege() -> None:
    world = make_siege_world()
    events = [siege_started(BESIEGER, TARGET_REGION, [BESIEGER_ARMY])]

    assert build_event_lines(events, world, "house_dunwick") == []
