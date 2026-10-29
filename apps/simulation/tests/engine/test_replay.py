from dataclasses import dataclass
from uuid import UUID

from app.engine.phases import Phase, PhaseContext, PhaseResult, ScenePause
from app.engine.pipeline import run_turn
from app.engine.world_init import new_world
from app.models.world_events import EventLogEntry, PhaseName, TurnStatus
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns_expanded
from strategy_contracts.scene import ProseOnlyOutcome, SceneType

from tests.engine.toy_phases import ToyPhase, toy_phases

PLAYTHROUGH_ID = UUID("11111111-1111-1111-1111-111111111111")
SCENE_ID = UUID("44444444-4444-4444-4444-444444444444")
SEED = 20261026
TURNS = 12
PAUSE_TURN = 2
DIVERGE_TURN = 4
SCENARIO = load_three_crowns_expanded()
GOLDEN_HASHES = [
    "16dc29985b5cb65e8c78aac9bd2cec4adfa6531e46a0e097e40578b53804edcc",
    "c4788df32ac301a94393e73620b9e76dc09d2aa2ff38fc8029fb7355d9e97ea1",
    "1c178356cb6f470416063f53e27c66d0223cdcee1f50fac076932270acae5bfa",
]


@dataclass
class Game:
    world: WorldState
    hashes: list[str]
    events: list[EventLogEntry]


def _start(seed: int = SEED) -> WorldState:
    ruler = PlayerRuler(
        name="Valdren",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
    )
    return new_world(SCENARIO, PLAYTHROUGH_ID, seed, "house_ashford", ruler)


def _play(phases: dict[PhaseName, Phase], seed: int = SEED, turns: int = TURNS) -> Game:
    game = Game(_start(seed), [], [])
    for _ in range(turns):
        result = run_turn(game.world, SCENARIO, [], phases, {}, {})
        assert result.status is TurnStatus.RESOLVED
        game.world = result.world
        game.hashes.append(result.world_hash)
        game.events += result.events
    return game


def _first_divergence(left: list[str], right: list[str]) -> int | None:
    for index, (a, b) in enumerate(zip(left, right, strict=True)):
        if a != b:
            return index
    return None


class PauseOnceAtTurn:
    """Wraps a phase; pauses on one turn until the scene outcome is supplied."""

    def __init__(self, inner: Phase, turn: int) -> None:
        self.name = inner.name
        self._inner = inner
        self._turn = turn

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        is_waiting = (
            world.clock.turn == self._turn
            and context.resolved_outcomes.get(world.progress.pending_scene_id) is None
        )
        if is_waiting:
            pause = ScenePause(SceneType.BATTLE_SPEECH, ("army_a",))
            return PhaseResult(world=world, pause=pause)
        return self._inner.run(world, context)


class ExtraDrawsSieges(ToyPhase):
    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        for _ in range(13):
            context.rng.next_u64()
        return super().run(world, context)


def test_two_runs_from_the_same_seed_have_identical_hashes() -> None:
    first = _play(toy_phases())
    second = _play(toy_phases())
    assert first.hashes == second.hashes
    assert first.events == second.events


def test_first_turns_match_the_recorded_golden_hashes() -> None:
    # NOTE: update deliberately when the world schema, hashing, seeding or toy
    # rules change; an accidental mismatch means replays of old games break.
    assert _play(toy_phases(), turns=len(GOLDEN_HASHES)).hashes == GOLDEN_HASHES


def test_the_world_changes_every_turn() -> None:
    hashes = _play(toy_phases()).hashes
    assert len(set(hashes)) == TURNS


def test_a_different_seed_diverges_from_the_first_turn() -> None:
    other = _play(toy_phases(), seed=SEED + 1)
    assert _first_divergence(_play(toy_phases()).hashes, other.hashes) == 0


def test_a_changed_rule_is_pinpointed_to_its_turn() -> None:
    def bump_gold_on_turn(world: WorldState, rng, context: PhaseContext) -> None:
        if world.clock.turn == DIVERGE_TURN:
            world.factions["house_carrow"].treasury += 1

    changed = ToyPhase(PhaseName.STORY_CHECK, bump_gold_on_turn)
    baseline = _play(toy_phases())
    altered = _play(toy_phases({PhaseName.STORY_CHECK: changed}))
    assert _first_divergence(baseline.hashes, altered.hashes) == DIVERGE_TURN


def test_extra_draws_in_one_phase_do_not_disturb_any_other_phase() -> None:
    baseline = _play(toy_phases())
    noisy = _play(toy_phases({PhaseName.SIEGES: ExtraDrawsSieges(PhaseName.SIEGES)}))
    assert baseline.hashes == noisy.hashes


def test_pause_and_resume_matches_an_uninterrupted_run() -> None:
    uninterrupted = _play(toy_phases())
    pausing = toy_phases(
        {PhaseName.BATTLES: PauseOnceAtTurn(ToyPhase(PhaseName.BATTLES), PAUSE_TURN)}
    )
    game = Game(_start(), [], [])
    for _ in range(TURNS):
        result = run_turn(game.world, SCENARIO, [], pausing, {}, {})
        game.events += result.events
        if result.status is TurnStatus.PAUSED:
            resumable = result.world.model_copy(deep=True)
            resumable.progress.pending_scene_id = SCENE_ID
            outcomes = {SCENE_ID: ProseOnlyOutcome()}
            result = run_turn(resumable, SCENARIO, [], pausing, outcomes, {})
            game.events += result.events
        game.world = result.world
        game.hashes.append(result.world_hash)
    assert game.hashes == uninterrupted.hashes
    assert game.events == uninterrupted.events


def test_event_sequence_numbers_are_gapless_across_turns() -> None:
    events = _play(toy_phases()).events
    assert [event.seq for event in events] == list(range(1, len(events) + 1))
