import type {
  CampaignWorldView,
  OperationGuard,
} from "../types/simulation.types";

export function buildOperationGuard(
  world: Pick<CampaignWorldView, "world_version" | "turn" | "wave"> & Partial<Pick<CampaignWorldView, "status">>,
  operationId: string = crypto.randomUUID(),
): OperationGuard {
  return {
    operation_id: operationId,
    expected_world_version: world.world_version,
    expected_turn: world.turn,
    expected_wave: world.wave + (
      world.status === "awaiting_commands" || world.status === "awaiting_battle_decision" ? 1 : 0
    ),
  };
}
