"""Pure rendering of a lore document into the plain text the narrator reads."""

from app.models.lore_document import LoreBlock, LoreDocument

BLOCK_SEPARATOR = "\n\n"


def _render_block(block: LoreBlock) -> str:
    text = block.text.strip()
    if not text:
        return ""
    if block.kind == "answer" and block.label:
        return f"{block.label}: {text}"
    return text


def render_lore_document(document: LoreDocument) -> str:
    rendered_blocks = (_render_block(block) for block in document.blocks)
    return BLOCK_SEPARATOR.join(block for block in rendered_blocks if block)
