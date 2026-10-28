"""What the clipboard shows, derived from the pinned rules and the hidden status.

TRS keeps a copy of this function (apps/turn-resolution-service/app/turn/
rule_sheet_view.py); the two case tables must stay identical.
"""

REVEALED_STATUS_EXCLUDED = "unrevealed"
CORRUPTED_STATUS = "corrupted"
DEFAULT_STATUS = "intact"


def rule_sheet_view(
    sheet_rules: list[dict[str, object]], rule_status: dict[str, object]
) -> list[dict[str, object]]:
    """Rules whose status is not `unrevealed`, ordered by display_order then
    number. A rule with no recorded status shows as its pinned initial status."""
    visible: list[tuple[int, int, dict[str, object]]] = []
    for rule in sheet_rules:
        status = _status_of(rule, rule_status)
        if status == REVEALED_STATUS_EXCLUDED:
            continue
        visible.append(
            (
                _int_of(rule, "display_order"),
                _int_of(rule, "number"),
                _item(rule, status),
            )
        )
    return [item for _order, _number, item in sorted(visible, key=lambda t: t[:2])]


def _status_of(rule: dict[str, object], rule_status: dict[str, object]) -> str:
    recorded = rule_status.get(str(rule.get("key")))
    if isinstance(recorded, str):
        return recorded
    initial = rule.get("initial_status")
    return initial if isinstance(initial, str) else DEFAULT_STATUS


def _int_of(rule: dict[str, object], name: str) -> int:
    value = rule.get(name)
    return value if isinstance(value, int) else 0


def _item(rule: dict[str, object], status: str) -> dict[str, object]:
    corrupted_text = rule.get("corrupted_text")
    is_swapped = status == CORRUPTED_STATUS and bool(corrupted_text)
    return {
        "key": rule.get("key"),
        "number": rule.get("number"),
        "text": corrupted_text if is_swapped else rule.get("text"),
        "status": status,
        "source_style": rule.get("source_style"),
    }
