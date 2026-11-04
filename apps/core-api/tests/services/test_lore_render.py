"""Unit tests for rendering lore documents to plain text."""

from app.models.lore_document import LoreBlock, LoreDocument
from app.services.lore_render import render_lore_document


def test_render_orders_blocks_and_prefixes_labels():
    document = LoreDocument(
        blocks=[
            LoreBlock(kind="text", text="Free text"),
            LoreBlock(
                kind="answer", question_id="voice", label="Voice", text="Slow and dry."
            ),
            LoreBlock(kind="text", text="Closing line"),
        ]
    )

    assert (
        render_lore_document(document)
        == "Free text\n\nVoice: Slow and dry.\n\nClosing line"
    )


def test_render_skips_empty_blocks():
    document = LoreDocument(
        blocks=[
            LoreBlock(kind="text", text="   "),
            LoreBlock(kind="answer", label="Voice", text=""),
            LoreBlock(kind="text", text="Kept"),
        ]
    )

    assert render_lore_document(document) == "Kept"


def test_render_empty_document_is_empty_string():
    assert render_lore_document(LoreDocument()) == ""


def test_render_answer_without_label_is_plain_text():
    document = LoreDocument(blocks=[LoreBlock(kind="answer", text="Just words")])

    assert render_lore_document(document) == "Just words"
