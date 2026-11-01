"""Writes the plant sheet the owner reviews before a corpus is frozen: `python -m eval.plant_sheet`."""

import sys
from pathlib import Path

from eval.corpus_loader import Campaign, load_campaign
from eval.corpus_models import PlantDef, ProbeDef

SHEET_FILE = "PLANT_SHEET.md"
MAX_ANCHOR_CHARS = 90


def _short(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= MAX_ANCHOR_CHARS else flat[: MAX_ANCHOR_CHARS - 1] + "…"


def _plant_cell(plant_id: str, plants: dict[str, PlantDef]) -> str:
    plant = plants[plant_id]
    where = f"t{plant.turn}" if plant.source in {"turn", "delta"} else plant.source
    return f"`{plant_id}` ({plant.kind}, {where}): {_short(plant.anchor_text)}"


def _probe_row(probe: ProbeDef, plants: dict[str, PlantDef]) -> str:
    required = "<br>".join(_plant_cell(p, plants) for p in probe.required) or "-"
    forbidden = [_plant_cell(p, plants) for p in probe.forbidden]
    forbidden += [f"marker: {_short(a)}" for a in probe.forbidden_anchors]
    distractors = "<br>".join(_plant_cell(p, plants) for p in probe.distractors) or "-"
    return (
        f"| `{probe.probe_id}` | {probe.failure_class} ({probe.style}) | {probe.at_turn} | "
        f"{probe.action_text} | {required} | {'<br>'.join(forbidden) or '-'} | "
        f"{distractors} | {probe.expected_truth} |"
    )


def campaign_section(campaign: Campaign) -> str:
    plants = {plant.plant_id: plant for plant in campaign.plants}
    header = (
        f"## {campaign.campaign_id} — {campaign.scenario.title} "
        f"({campaign.scenario.mode}, {len(campaign.turns)} turns, "
        f"{len(campaign.probes)} probes)"
    )
    columns = "| probe | class (style) | after turn | question | required evidence | forbidden | wrong referents | expected truth |"
    divider = "|---|---|---|---|---|---|---|---|"
    rows = [_probe_row(probe, plants) for probe in campaign.probes]
    return "\n".join([header, "", columns, divider, *rows])


def build_sheet(campaigns: list[Campaign]) -> str:
    intro = (
        "# Plant sheet — review before the corpus is frozen\n\n"
        "Every anchor is a verbatim sentence in the named turn, card or lore. "
        "Edit `turns.jsonl`, `plants.jsonl` or `probes.jsonl` in place, then run "
        "`python -m eval.corpus_validate` and `python -m eval.labels eval/corpus/<id>`."
    )
    return "\n\n".join([intro, *(campaign_section(c) for c in campaigns)]) + "\n"


def main(corpus_root: Path) -> Path:
    campaigns = [load_campaign(p) for p in sorted(corpus_root.iterdir()) if p.is_dir()]
    target = corpus_root / SHEET_FILE
    target.write_text(build_sheet(campaigns), encoding="utf-8")
    return target


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("eval/corpus")
    print(main(root))
