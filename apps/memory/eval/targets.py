"""The accepted per-class targets of `eval/targets.json`."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from eval.errors import HarnessError

TARGETS_FILE = Path(__file__).parent / "targets.json"

Statistic = Literal["lower_bound", "mean", "mean_over_runs", "max_over_runs", "count"]
Comparator = Literal[">=", "<=", "=="]
TargetStatus = Literal["active", "deferred"]


class Target(BaseModel):
    id: str
    scope: str
    metric: str
    statistic: Statistic
    comparator: Comparator
    value: float | None
    status: TargetStatus
    note: str = ""


class TargetsFile(BaseModel):
    source: str
    corpus_version: int
    statistics: dict[str, str] = Field(default_factory=dict)
    targets: list[Target]

    @property
    def active(self) -> list[Target]:
        return [t for t in self.targets if t.status == "active"]


def load_targets(path: Path = TARGETS_FILE) -> TargetsFile:
    if not path.exists():
        raise HarnessError(f"Targets file {path} does not exist")
    targets = TargetsFile.model_validate_json(path.read_text(encoding="utf-8"))
    missing = [t.id for t in targets.active if t.value is None]
    if missing:
        raise HarnessError(f"Active targets without a value: {', '.join(missing)}")
    return targets
