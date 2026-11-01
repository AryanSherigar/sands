"""Renders a fact as one readable line for recall. Pure, no I/O."""

PREDICATE_WORD_SEPARATOR = "_"


def render_fact_text(subject_name: str, predicate: str, object_text: str) -> str:
    predicate_words = predicate.replace(PREDICATE_WORD_SEPARATOR, " ")
    parts = (subject_name, predicate_words, object_text)
    return " ".join(part for part in parts if part)
