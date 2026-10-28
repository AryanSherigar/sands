import { useStrategyPlayStore } from "../stores/strategyPlay.store";
import type { StrategyDiplomacyProps } from "../types/scene.types";
import type { CampaignWorldView } from "../types/simulation.types";
import { useOpenNegotiation } from "./useOpenNegotiation";

const NO_PACTS: StrategyDiplomacyProps["pacts"] = [];

export function useStrategyDiplomacy(
  playthroughId: string | undefined,
  world: CampaignWorldView,
) {
  const { openNegotiation, isOpening, errorMessage } = useOpenNegotiation(playthroughId);
  const activeSceneId = useStrategyPlayStore((state) => state.activeSceneId);

  const pendingSceneId = world.status === "awaiting_scene" ? (world.scene_id ?? null) : null;
  const sceneId = activeSceneId ?? pendingSceneId;

  const diplomacy: StrategyDiplomacyProps = {
    pacts: world.pacts ?? NO_PACTS,
    isProposalAvailable:
      Boolean(playthroughId) && world.status === "planning" && !isOpening,
    onProposeTerms: openNegotiation,
  };

  return { diplomacy, sceneId, errorMessage };
}
