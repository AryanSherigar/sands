from uuid import uuid4

from app.services.dispatch_prompt import PERSONA_MARKER, build_dispatch_prompt
from strategy_contracts.agents import AgentTrait, AgentView, DispatchBriefing
from strategy_contracts.pressure import PressureBand, RumorTopic
from tests.turn.prefix_stability import assert_shared_through

FORBIDDEN_WORDS = ("bribe", "bribed", "true", "loyal", "poison", "lie", "hint")


def _briefing(
    traits: list[AgentTrait] | None = None,
    topic: RumorTopic = RumorTopic.WILL,
    band: PressureBand = PressureBand.HIGH,
    name: str = "Aldous",
) -> DispatchBriefing:
    return DispatchBriefing(
        rumor_id="rumor_1",
        playthrough_id=uuid4(),
        turn=4,
        agent=AgentView(name=name, traits=traits or [AgentTrait.HONEST]),
        about_faction_id="house_dunwick",
        topic=topic,
        reported_band=band,
    )


def test_prompt_states_the_reported_band_and_agent_name_as_fact() -> None:
    prompt = build_dispatch_prompt(_briefing(band=PressureBand.VERY_HIGH))

    assert "very high" in prompt.user
    assert "House Dunwick" in prompt.user
    assert "Aldous" in prompt.system


def test_prompt_uses_the_visible_trait_voice() -> None:
    plain = build_dispatch_prompt(_briefing([AgentTrait.HONEST]))
    pious = build_dispatch_prompt(_briefing([AgentTrait.PIOUS]))

    assert plain.system != pious.system
    assert "devotion" in pious.system


def test_prompt_never_mentions_bribery_truth_or_loyalty() -> None:
    for traits in ([AgentTrait.DECEITFUL, AgentTrait.PIOUS], [AgentTrait.INCOMPETENT]):
        prompt = build_dispatch_prompt(_briefing(traits))
        text = (prompt.system + prompt.user).lower()
        for word in FORBIDDEN_WORDS:
            assert word not in text, word


def test_trait_order_is_stable() -> None:
    first = build_dispatch_prompt(_briefing([AgentTrait.PIOUS, AgentTrait.HONEST]))
    second = build_dispatch_prompt(_briefing([AgentTrait.HONEST, AgentTrait.PIOUS]))

    assert first.system == second.system


def test_two_dispatches_share_the_rules_head_through_the_persona_marker() -> None:
    first = build_dispatch_prompt(_briefing(name="Aldous"))
    second = build_dispatch_prompt(
        _briefing([AgentTrait.PIOUS], RumorTopic.STRAIN, name="Maren")
    )

    assert_shared_through(first.system, second.system, PERSONA_MARKER)


def test_same_agent_dispatches_have_identical_system_instruction() -> None:
    first = build_dispatch_prompt(_briefing(topic=RumorTopic.WILL))
    second = build_dispatch_prompt(
        _briefing(topic=RumorTopic.THREAT, band=PressureBand.LOW)
    )

    assert first.system == second.system
    assert first.user != second.user
