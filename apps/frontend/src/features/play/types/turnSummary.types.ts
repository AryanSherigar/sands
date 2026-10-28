import { InventoryChange, StatChange } from "./play.types";

// Wire shape of TRS's `turn_summary` SSE event
// (turn-resolution-service/app/models/turn_summary.py::TurnSummaryPayload).
// Dice rolls are surfaced separately via the "check_resolved" SSE event
// (shared/types/check.types.ts), not here.
export interface TurnSummaryEventPayload {
  stat_changes: StatChange[];
  inventory_changes: InventoryChange[];
  active_conditions: string[];
}
