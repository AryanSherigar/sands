from app.services import scene_prompt
from strategy_contracts.scene import ScenePackage, SceneType
from strategy_contracts.scene_exchange import SceneExchangeView
from tests.services.revolt_fixtures import revolt_package
from tests.turn.prefix_stability import assert_shared_through


def _package() -> ScenePackage:
    return revolt_package()


def _render(system: str, contents) -> str:
    parts = [system] + [
        f"{item.role}: {part.text}" for item in contents for part in item.parts
    ]
    return "\n".join(parts)


def test_the_brief_lists_the_menu_ids_and_the_grievance() -> None:
    system = scene_prompt.build_system_instruction(_package())
    brief = system.split("PRIVATE BRIEF")[1]

    assert "- charter: Grant a charter" in brief
    assert "petition against the burden of taxes" in brief


def test_the_private_brief_stays_out_of_user_and_model_turns() -> None:
    transcript = [
        SceneExchangeView(sequence=1, player_text="Hear me.", leader_text="Speak.")
    ]
    contents = scene_prompt.build_reply_contents(
        transcript, "I will lower the tax.", 4, SceneType.REVOLT_TALK
    )
    contents += scene_prompt.build_decision_contents(
        transcript, "I will lower the tax.", "We hear you.", 4, SceneType.REVOLT_TALK
    )
    text = " ".join(part.text for item in contents for part in item.parts)

    assert "PRIVATE BRIEF" not in text
    assert "charter" not in text


def test_two_consecutive_exchanges_share_the_system_and_first_quote() -> None:
    system = scene_prompt.build_system_instruction(_package())
    first = scene_prompt.build_reply_contents([], "Hear me.", 4, SceneType.REVOLT_TALK)
    second = scene_prompt.build_reply_contents(
        [SceneExchangeView(sequence=1, player_text="Hear me.", leader_text="Speak.")],
        "Taxes will fall.",
        4,
        SceneType.REVOLT_TALK,
    )

    assert_shared_through(
        _render(system, first), _render(system, second), "</player_says>"
    )


def test_the_decision_directive_asks_for_a_menu_id() -> None:
    directive = scene_prompt.profile_for(SceneType.REVOLT_TALK).decision_directive

    assert "choose_option" in directive
    assert "no_terms" in directive
