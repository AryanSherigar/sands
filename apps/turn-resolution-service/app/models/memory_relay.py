"""Result shapes for the memory outbox relay."""

from pydantic import BaseModel


class RelaySummary(BaseModel):
    """Counts from one relay pass; ids and counts only, never content."""

    playthroughs_attempted: int = 0
    rows_delivered: int = 0
    rows_failed: int = 0

    def plus(self, other: "RelaySummary") -> "RelaySummary":
        return RelaySummary(
            playthroughs_attempted=self.playthroughs_attempted
            + other.playthroughs_attempted,
            rows_delivered=self.rows_delivered + other.rows_delivered,
            rows_failed=self.rows_failed + other.rows_failed,
        )
