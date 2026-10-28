from dataclasses import dataclass

from app.models.battle_command import Command
from strategy_contracts.stances import ScoreCategory


@dataclass(frozen=True)
class Candidate:
    order: Command
    category: ScoreCategory
    base_score: int = 0


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Candidate
    score: int
    trait_score: int
    stance_score: int
    aim_score: int = 0
    adjustment: int = 0
