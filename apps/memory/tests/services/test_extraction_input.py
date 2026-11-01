"""Pure rendering helpers of the extraction input builder."""

from uuid import uuid4

from app.models.facts import EntityRow
from app.models.templates import ParticipantPayload
from app.services.extraction_input import (
    ParticipantNames,
    load_system_prompt,
    render_roster,
    render_user_content,
)


def _entity(name: str, *, is_player: bool = False) -> EntityRow:
    return EntityRow(
        entity_id=uuid4(),
        scope_kind="playthrough",
        scope_id=uuid4(),
        entity_type="character",
        canonical_name=name,
        provenance="authored",
        first_seen_seq=0,
        is_player=is_player,
    )


def test_registered_participants_use_their_display_names() -> None:
    participant_id = uuid4()
    names = ParticipantNames(
        [ParticipantPayload(participant_id=participant_id, display_name="Mira")]
    )

    assert names.name_of(participant_id) == "Mira"


def test_unregistered_participants_get_stable_letter_labels() -> None:
    first, second = uuid4(), uuid4()
    names = ParticipantNames([])

    assert names.name_of(first) == "Player A"
    assert names.name_of(second) == "Player B"
    assert names.name_of(first) == "Player A"


def test_roster_marks_the_player_character() -> None:
    player, other = _entity("The Wanderer", is_player=True), _entity("Captain Vale")

    rendered = render_roster([player, other])

    assert (
        f"{player.entity_id} | character | The Wanderer | player character" in rendered
    )
    assert rendered.splitlines()[1].endswith("Captain Vale")


def test_empty_roster_renders_none() -> None:
    assert render_roster([]) == "(none)"


def test_user_content_contains_every_section_in_order() -> None:
    content = render_user_content("T", "C", "R", "F", "S")

    positions = [
        content.index(heading)
        for heading in ("TRACKED STATE", "ROSTER", "CONTEXT", "CURRENT SCENE", "TURNS")
    ]
    assert positions == sorted(positions)


def test_system_prompt_treats_turn_text_as_data() -> None:
    assert "quoted data" in load_system_prompt()


def _prompt_versions() -> list[str]:
    from typing import get_args

    from app.config import Settings

    return list(get_args(Settings.model_fields["extraction_prompt_version"].annotation))


def test_every_selectable_prompt_version_has_a_prompt_file() -> None:
    for version in _prompt_versions():
        assert "quoted data" in load_system_prompt(version)


def test_prompt_v2_differs_from_v1_but_keeps_the_lore_mode_section() -> None:
    first = load_system_prompt("extraction_v1")
    second = load_system_prompt("extraction_v2")
    assert first != second
    first_lore = first[first.index("LORE MODE") :].strip()
    assert first_lore == second[second.index("LORE MODE") :].strip()


def test_prompt_v2_example_output_is_valid_against_the_extraction_schema() -> None:
    from app.models.extraction import ExtractionOutput

    prompt = load_system_prompt("extraction_v2")
    example = prompt.split("Output:\n", 1)[1].split("\n", 1)[0]
    output = ExtractionOutput.model_validate_json(example)
    assert output.facts and output.new_commitments and output.scene is None
    assert not any("not" in fact.predicate for fact in output.facts)


def test_new_batches_carry_the_configured_prompt_version() -> None:
    from uuid import uuid4

    from app.config import Settings
    from app.models.templates import PlaythroughRow
    from app.services.extraction_batches import _playthrough_batch

    playthrough = PlaythroughRow(
        playthrough_id=uuid4(),
        template_id=None,
        ingested_seq=5,
        indexed_seq=5,
        extracted_seq=0,
        latest_seq_seen=5,
        flush_requested_through_seq=None,
        created_at="2026-10-27T00:00:00Z",
    )
    first = _playthrough_batch(playthrough, Settings())
    second = _playthrough_batch(
        playthrough, Settings(extraction_prompt_version="extraction_v2")
    )
    assert (first.prompt_version, second.prompt_version) == (
        "extraction_v1",
        "extraction_v2",
    )


def test_prompt_v3_keeps_the_v2_example_and_adds_a_refused_change_example() -> None:
    from app.models.extraction import ExtractionOutput

    second = load_system_prompt("extraction_v2")
    third = load_system_prompt("extraction_v3")
    assert third != second
    assert third[third.index("LORE MODE") :] == second[second.index("LORE MODE") :]
    assert "SECOND EXAMPLE (a refused change)" in third
    examples = [part.split("\n", 1)[0] for part in third.split("Output:\n")[1:]]
    outputs = [ExtractionOutput.model_validate_json(example) for example in examples]
    assert outputs[0].facts and not outputs[1].facts


def test_context_without_facts_keeps_only_commitments() -> None:
    from uuid import uuid4

    from app.models.retrieve import ExtractionContext, MemoryItem
    from app.services.extraction_input import _render_context

    def item(kind: str, text: str) -> MemoryItem:
        return MemoryItem(
            kind=kind,  # type: ignore[arg-type]
            item_id=uuid4(),
            source_kind="extraction",
            authority="extracted",
            assertion=None,
            sequence=1,
            speaker=None,
            text=text,
            entity_ids=[],
            branches=["exact"],
        )

    context = ExtractionContext(
        lines=[],
        items=[item("fact", "Pip lodges at the inn"), item("commitment", "Pay Wick")],
        entity_ids=[],
        token_count=0,
        truncated=False,
    )

    assert "Pip lodges" in _render_context(context)
    trimmed = _render_context(context, has_facts=False)
    assert "Pip lodges" not in trimmed
    assert "Pay Wick" in trimmed


def test_the_supersession_judge_prompt_treats_the_input_as_data() -> None:
    prompt = load_system_prompt("supersession_v1")
    assert "quoted data" in prompt
    assert "superseded_fact_id" in prompt
