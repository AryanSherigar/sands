"""Loads one campaign directory into typed models and fingerprints its content."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from eval.corpus_models import PlantDef, ProbeDef, ScenarioFile, TurnDef

SCENARIO_FILE = "scenario.json"
TURNS_FILE = "turns.jsonl"
DECOY_FILE = "decoy.jsonl"
PLANTS_FILE = "plants.jsonl"
PROBES_FILE = "probes.jsonl"
CONTENT_FILES = (SCENARIO_FILE, TURNS_FILE, DECOY_FILE, PLANTS_FILE, PROBES_FILE)

LineModel = TypeVar("LineModel", bound=BaseModel)


class CorpusLoadError(RuntimeError):
    """A corpus file is missing or does not parse."""


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    scenario: ScenarioFile
    turns: list[TurnDef]
    decoy_turns: list[TurnDef]
    plants: list[PlantDef]
    probes: list[ProbeDef]
    content_hash: str


def _read_lines(
    path: Path, model: type[LineModel], is_required: bool
) -> list[LineModel]:
    if not path.is_file():
        if is_required:
            raise CorpusLoadError(f"Missing corpus file {path}")
        return []
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    return [model.model_validate_json(line) for line in lines]


def content_hash_of(directory: Path) -> str:
    digest = hashlib.sha256()
    for name in CONTENT_FILES:
        path = directory / name
        if path.is_file():
            digest.update(name.encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def load_campaign(directory: Path) -> Campaign:
    scenario_path = directory / SCENARIO_FILE
    if not scenario_path.is_file():
        raise CorpusLoadError(f"Missing corpus file {scenario_path}")
    scenario = ScenarioFile.model_validate_json(
        scenario_path.read_text(encoding="utf-8")
    )
    return Campaign(
        campaign_id=scenario.campaign_id,
        scenario=scenario,
        turns=_read_lines(directory / TURNS_FILE, TurnDef, True),
        decoy_turns=_read_lines(directory / DECOY_FILE, TurnDef, False),
        plants=_read_lines(directory / PLANTS_FILE, PlantDef, True),
        probes=_read_lines(directory / PROBES_FILE, ProbeDef, True),
        content_hash=content_hash_of(directory),
    )
