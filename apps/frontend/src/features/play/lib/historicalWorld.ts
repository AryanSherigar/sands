import type { CampaignWorldView } from "../types/simulation.types";
import { parseCampaignWorld } from "./campaignWorldParser";

export interface HistoricalWorldResponse {
  turn: number;
  world_hash: string;
  world: Record<string, unknown>;
}

// NOTE: a past turn is shown read-only, so anything that asks the player to act is emptied.
const QUIET_FIELDS = {
  battles: [],
  pending_events: [],
  uprisings: [],
  pending_calls: [],
  pending_demands: [],
  queued_orders: [],
  pending_scene: null,
} as const;

export function adaptHistoricalWorld(response: HistoricalWorldResponse): CampaignWorldView {
  return parseCampaignWorld({
    ...response.world,
    ...QUIET_FIELDS,
    turn: response.turn,
    wave: 0,
    world_version: 0,
    world_hash: response.world_hash,
    status: "turn_completed",
  });
}
