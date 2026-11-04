from app.models.sheet_rule import SheetRuleCreate


def test_ink_block_is_a_valid_hand() -> None:
    rule = SheetRuleCreate(key="r6_block", number=6, text="x", source_style="ink_block")
    assert rule.source_style == "ink_block"
