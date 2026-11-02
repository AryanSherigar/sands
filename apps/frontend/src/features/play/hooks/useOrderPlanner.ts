import { useStrategyPlayStore } from "../stores/strategyPlay.store";
import {
  buildAnswerCallOrder,
  buildAnswerDemandOrder,
  buildAttackOrder,
  buildBesiegeOrder,
  buildCallNegotiationOrder,
  buildDeclareWarOrder,
  buildDisbandOrder,
  buildFabricateClaimOrder,
  buildHaltOrder,
  buildLevyOrder,
  buildMapScoutOrder,
  buildMoveOrder,
  buildSendEnvoyOrder,
  buildSetPayOrder,
  buildSuePeaceOrder,
} from "../lib/orderBuilders";
import { parseSimulationError } from "../lib/simulationError";
import { PREVIEW_ORDERS_DISABLED_MESSAGE } from "../constants/strategy.constants";
import type { StrategyInspectorAction } from "../types/strategyActions.types";
import type { CampaignWorldView, StrategyOrder } from "../types/simulation.types";
import { useSimulationCommands } from "./useSimulationCommands";

const SUBMIT_FAILURE_MESSAGE = "Could not issue that order";
const HISTORY_VIEW_MESSAGE = "You are looking at a past turn. Return to the present to give orders.";
const CAMPAIGN_ENDED_MESSAGE = "The campaign has ended. No more orders can be given.";
const REFUSED_FALLBACK_MESSAGE = "That order cannot be issued right now";

export function useOrderPlanner(playthroughId: string | undefined, world: CampaignWorldView) {
  const { acceptMutation, check } = useSimulationCommands(playthroughId);
  const targeting = useStrategyPlayStore((state) => state.targeting);
  const startTargeting = useStrategyPlayStore((state) => state.startTargeting);
  const cancelTargeting = useStrategyPlayStore((state) => state.cancelTargeting);
  const setOrderFeedback = useStrategyPlayStore((state) => state.setOrderFeedback);
  const isViewingHistory = useStrategyPlayStore((state) => state.historyTurn !== null);
  const setPendingWarTarget = useStrategyPlayStore((state) => state.setPendingWarTarget);
  const groupArmyIds = useStrategyPlayStore((state) => state.groupArmyIds);
  const clearGroupArmies = useStrategyPlayStore((state) => state.clearGroupArmies);
  const factionId = world.my_faction.id;

  const submitOrder = async (order: StrategyOrder): Promise<void> => {
    if (!playthroughId) {
      setOrderFeedback({ message: PREVIEW_ORDERS_DISABLED_MESSAGE });
      return;
    }
    if (isViewingHistory) {
      setOrderFeedback({ message: HISTORY_VIEW_MESSAGE });
      return;
    }
    if (world.ending) {
      setOrderFeedback({ message: CAMPAIGN_ENDED_MESSAGE });
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
    if (action.type === "besiege") {
      const army = world.armies.find((item) => item.army_id === action.armyId);
      if (army) void submitOrder(buildBesiegeOrder(factionId, army.army_id, army.location_id));
      return;
    }
    if (action.type === "halt") {
      void submitOrder(buildHaltOrder(factionId, action.armyId));
      return;
    }
    if (action.type === "disband") {
      void submitOrder(buildDisbandOrder(factionId, action.armyId));
      return;
    }
    if (action.type === "map_scout") {
      void submitOrder(buildMapScoutOrder(factionId, action.regionId));
      return;
    }
    if (action.type === "fabricate_claim") {
      void submitOrder(buildFabricateClaimOrder(factionId, action.targetFactionId, action.regionId));
      return;
    }
    if (action.type === "set_pay") {
      void submitOrder(buildSetPayOrder(factionId, action.armyId, action.payLevel));
      return;
    }
    if (action.type === "declare_war") {
      const hasGrounds = (world.usable_grounds ?? []).some((ground) => ground.target_faction_id === action.targetFactionId);
      if (hasGrounds) setPendingWarTarget(action.targetFactionId);
      else void submitOrder(buildDeclareWarOrder(factionId, action.targetFactionId));
      return;
    }
    if (action.type === "sue_peace") {
      void submitOrder(buildSuePeaceOrder(factionId, action.warId));
      return;
    }
    if (action.type === "send_envoy") {
      void submitOrder(buildSendEnvoyOrder(factionId, action.targetFactionId));
      return;
    }
    if (action.type === "call_negotiation") {
      void submitOrder(buildCallNegotiationOrder(factionId, action.targetFactionId));
      return;
    }
    if (action.type === "answer_call") {
      void submitOrder(buildAnswerCallOrder(factionId, action.callId, action.isJoining));
      return;
    }
    if (action.type === "answer_demand") {
      void submitOrder(buildAnswerDemandOrder(factionId, action.demandId, action.reply));
      return;
    }
    if (action.type === "levy") {
      const region = world.regions.find((item) => item.region_id === action.regionId);
      if (region) void submitOrder(buildLevyOrder(factionId, region));
    }
  };

  const submitInSequence = async (orders: StrategyOrder[]): Promise<void> => {
    for (const order of orders) {
      await submitOrder(order);
    }
  };

  const handleGroupAction = (action: "move" | "halt"): void => {
    if (groupArmyIds.length === 0) return;
    setOrderFeedback(null);
    if (action === "halt") {
      const orders = groupArmyIds.map((armyId) => buildHaltOrder(factionId, armyId));
      clearGroupArmies();
      void submitInSequence(orders);
      return;
    }
    startTargeting({ action: "move", sourceArmyId: groupArmyIds[0] ?? "", groupArmyIds });
  };

  const handleRegionTargeted = (regionId: string): void => {
    if (!targeting) return;
    const { action, sourceArmyId, groupArmyIds: groupIds } = targeting;
    cancelTargeting();
    const armyIds = groupIds && groupIds.length > 0 ? groupIds : [sourceArmyId];
    const orders = armyIds.map((armyId) =>
      action === "move"
        ? buildMoveOrder(factionId, armyId, regionId)
        : buildAttackOrder(factionId, armyId, regionId),
    );
    if (groupIds) clearGroupArmies();
    void submitInSequence(orders);
  };

  return {
    targeting,
    submitOrder,
    handleInspectorAction,
    handleGroupAction,
    handleRegionTargeted,
    cancelTargeting,
  };
}
