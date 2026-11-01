"""Per-request inputs to every retrieval eligibility predicate."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EligibilityContext(BaseModel):
    """`template_id` None means playthrough scope only. `should_include_hidden` lifts
    the reveal test for hidden authored items (extraction context); conditional items
    still require `active_conditional_authored_fact_ids`."""

    model_config = ConfigDict(frozen=True)

    playthrough_id: UUID
    template_id: UUID | None
    at_seq: int = Field(ge=0)
    recent_window_turns: int = Field(ge=0)
    revealed_authored_fact_ids: list[UUID] = Field(default_factory=list)
    active_conditional_authored_fact_ids: list[UUID] = Field(default_factory=list)
    should_include_hidden: bool = False

    def to_params(self) -> dict[str, object]:
        return {
            "playthrough_id": self.playthrough_id,
            "template_id": self.template_id,
            "at_seq": self.at_seq,
            "recent_window_turns": self.recent_window_turns,
            "revealed_authored_fact_ids": self.revealed_authored_fact_ids,
            "active_conditional_authored_fact_ids": (
                self.active_conditional_authored_fact_ids
            ),
            "should_include_hidden": self.should_include_hidden,
        }
