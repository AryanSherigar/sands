"""The rules on the clipboard (prose doc §5; hands from the scenario doc §6).

Rule 6 is two rows with one number: the narrator's seed reveals either the
leaning hand (`r6`) or the upright block hand (`r6_block`), never both.
"""

from app.models.sheet_rule import SheetRuleCreate
from scripts.night_desk import prose, schema

SOURCE_STYLES = {
    "r1": "typed",
    "r2": "typed",
    "r3": "typed",
    "r4": "typed",
    "r6": "ink",
    "r6_block": "ink_block",
    "r7": "printed",
    "r8": "spoken",
}
RULE_NUMBERS = {"r6_block": 6}
FLAGGABLE_RULES = frozenset({"r2"})
PROSE_KEYS = {"r6_block": "r6"}


def _rule_number(key: str) -> int:
    return RULE_NUMBERS.get(key) or int(key.removeprefix("r"))


def sheet_rules() -> list[SheetRuleCreate]:
    rules: list[SheetRuleCreate] = []
    for index, key in enumerate(schema.RULE_IDS):
        is_revealed = key in schema.INITIALLY_REVEALED
        rules.append(
            SheetRuleCreate(
                key=key,
                number=_rule_number(key),
                text=prose.STANDING_INSTRUCTIONS[PROSE_KEYS.get(key, key)],
                initial_status="intact" if is_revealed else "unrevealed",
                source_style=SOURCE_STYLES[key],
                is_ai_flaggable=key in FLAGGABLE_RULES,
                display_order=index,
            )
        )
    return rules
