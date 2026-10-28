import { useStrategyPlayStore } from "../stores/strategyPlay.store";
import {
  buildAttackOrder,
  buildHaltOrder,
  buildLevyOrder,
  buildMoveOrder,
} from "../lib/orderBuilders";
import { parseSimulationError } from "../lib/simulationError";
import { PREVIEW_ORDERS_DISABLED_MESSAGE } from "../constants/strategy.constants";
import type { StrategyInspectorAction } from "../types/strategyActions.types";
import type { CampaignWorldView, StrategyOrder } from "../types/simulation.types";
import { useSimulationCommands } from "./useSimulationCommands";

const SUBMIT_FAILURE_MESSAGE = "Could not issue that order";
const REFUSED_FALLBACK_MESSAGE = "That order cannot be issued right now";

export function useOrderPlanner(playthroughId: string | undefined, world: CampaignWorldView) {
  const { acceptMutation, check } = useSimulationCommands(playthroughId);
  const targeting = useStrategyPlayStore((state) => state.targeting);
  const startTargeting = useStrategyPlayStore((state) => state.startTargeting);
  const cancelTargeting = useStrategyPlayStore((state) => state.cancelTargeting);
  const setOrderFeedback = useStrategyPlayStore((state) => state.setOrderFeedback);
  const factionId = world.my_faction.id;

  const submitOrder = async (order: StrategyOrder): Promise<void> => {
    if (!playthroughId) {
      setOrderFeedback({ message: PREVIEW_ORDERS_DISABLED_MESSAGE });
      return;
    }
    try {
      const verdict = await check(order);
      if (verdict.flag) {
        setOrderFeedback({ message: verdict.reason ?? REFUSED_FALLBACK_MESSAGE });
        return;
      }
      await acceptMutation.mutateAsync(order);
      setOrderFeedback(null);
    } catch (error) {
      setOrderFeedback({ message: parseSimulationError(error, SUBMIT_FAILURE_MESSAGE).message });
    }
  };

  const handleInspectorAction = (action: StrategyInspectorAction): void => {
    setOrderFeedback(null);
    if (action.type === "move" || action.type === "attack") {
      startTargeting({ action: action.type, sourceArmyId: action.armyId });
      return;
    }
    if (action.type === "halt") {
      void submitOrder(buildHaltOrder(factionId, action.armyId));
      return;
    }
    const region = world.regions.find((item) => item.region_id === action.regionId);
    if (region) void submitOrder(buildLevyOrder(factionId, region));
  };

  const handleRegionTargeted = (regionId: string): void => {
    if (!targeting) return;
    const { action, sourceArmyId } = targeting;
    cancelTargeting();
    const order =
      action === "move"
        ? buildMoveOrder(factionId, sourceArmyId, regionId)
        : buildAttackOrder(factionId, sourceArmyId, regionId);
    void submitOrder(order);
  };

  return {
    targeting,
    submitOrder,
    handleInspectorAction,
    handleRegionTargeted,
    cancelTargeting,
  };
}
