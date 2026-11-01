from app.services.fact_text import render_fact_text


def test_predicate_underscores_become_spaces() -> None:
    assert (
        render_fact_text("Kestrel Vane", "member_of", "The Vigil")
        == "Kestrel Vane member of The Vigil"
    )


def test_empty_parts_are_skipped() -> None:
    assert render_fact_text("Mira", "rank", "") == "Mira rank"
