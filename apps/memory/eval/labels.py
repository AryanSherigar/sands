"""Extraction labels derived from a campaign's plant-list, never maintained by hand."""

import sys
from pathlib import Path
from typing import Literal

from eval.corpus_loader import Campaign, load_campaign
from eval.corpus_models import CorpusModel, PlantDef

LABELS_DIRECTORY = "labels"
LABELS_FILE = "extraction.jsonl"

LabelType = Literal[
    "fact", "commitment", "supersession", "entity_link", "forbidden_fact"
]
LABEL_TYPE_BY_KIND: dict[str, LabelType] = {
    "fact": "fact",
    "relation": "fact",
    "commitment": "commitment",
    "supersession": "supersession",
    "entity_link": "entity_link",
    "rejected": "forbidden_fact",
    "negated": "forbidden_fact",
}


class ExtractionLabel(CorpusModel):
    label_id: str
    label_type: LabelType
    turn: int
    anchor_text: str
    subject_key: str | None = None
    predicate: str | None = None
    object_key: str | None = None
    object_literal: str | None = None
    commitment_kind: str | None = None
    status: str | None = None
    supersedes_label_id: str | None = None


def _label_for(plant: PlantDef) -> ExtractionLabel:
    return ExtractionLabel(
        label_id=plant.plant_id,
        label_type=LABEL_TYPE_BY_KIND[plant.kind],
        turn=plant.turn,
        anchor_text=plant.anchor_text,
        subject_key=plant.subject_key,
        predicate=plant.predicate,
        object_key=plant.object_key,
        object_literal=plant.object_literal,
        commitment_kind=plant.commitment_kind,
        status=plant.status,
        supersedes_label_id=plant.supersedes_plant_id,
    )


def generate_labels(campaign: Campaign) -> list[ExtractionLabel]:
    return [_label_for(plant) for plant in campaign.plants if plant.source == "turn"]


def write_labels(directory: Path) -> int:
    labels = generate_labels(load_campaign(directory))
    target = directory / LABELS_DIRECTORY
    target.mkdir(exist_ok=True)
    lines = [label.model_dump_json(exclude_none=True) for label in labels]
    (target / LABELS_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(labels)


if __name__ == "__main__":
    for argument in sys.argv[1:]:
        print(argument, write_labels(Path(argument)))
