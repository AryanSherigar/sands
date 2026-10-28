import { useState, useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSceneView } from "../api/scene.api";
import { chooseEconomyOutcome } from "../api/simulation.api";
import { buildOperationGuard } from "../lib/operationGuard";
import { getWorldQueryKey } from "./useSimulationCommands";
import type { StrategyEventPackage } from "../types/eventScene.types";
import type { CampaignWorldView, EconomyChoice } from "../types/simulation.types";

const SHORTFALL_SCENE_TYPES = ["event", "economy", "shortfall"];
const ECONOMY_CHOICES: readonly string[] = ["shortfall_take_loan", "shortfall_default"];

function formatShortfallEvent(
  sceneId: string,
  world?: CampaignWorldView | null,
): StrategyEventPackage {
  const turn = world?.turn ?? 1;
  const year = world?.clock?.start_year ?? 1042;
  return {
    sceneId,
    category: "trouble",
    title: "Trouble: Treasury Shortfall",
    subheading: "Crown Exchequer Jurisdiction",
    turnText: `Turn ${turn} • Year ${year}`,
    bodyProse:
      "The crown treasury is depleted and cannot cover military upkeep and administrative expenses for this cycle. Immediate action is required to avoid troop desertion.",
    causeQuote:
      "Because expenditures exceeded tax revenues and state reserves were exhausted.",
    character: {
      name: "Lord High Treasurer",
      title: "Chancellor of the Exchequer",
      disposition: "Distressed",
    },
    choices: [
      {
        id: "shortfall_take_loan",
        label: "Contract Emergency Merchant Loan",
        effects: ["Gold +Credit", "Orders Next Turn −1", "Debt +10% Interest"],
      },
      {
        id: "shortfall_default",
        label: "Declare Sovereign Default",
        effects: ["Unpaid Troops Desert", "Stability −2", "Orders Next Turn −1"],
      },
    ],
  };
}

function readSceneId(world?: CampaignWorldView | null): string | null {
  return world?.pending_scene?.scene_id ?? world?.scene_id ?? null;
}

function isEconomyChoice(value: string): value is EconomyChoice {
  return ECONOMY_CHOICES.includes(value);
}

function isShortfallScene(sceneType: string | undefined): boolean {
  return sceneType !== undefined && SHORTFALL_SCENE_TYPES.includes(sceneType);
}

export function useStrategyEvent(
  playthroughId?: string,
  world?: CampaignWorldView | null,
  onResolved?: () => void,
) {
  const queryClient = useQueryClient();
  const [isResolving, setIsResolving] = useState(false);
  const [eventPackage, setEventPackage] = useState<StrategyEventPackage | null>(null);

  const isAwaitingScene = world?.status === "awaiting_scene";
  const sceneId = readSceneId(world);
  const pendingSceneType = world?.pending_scene?.scene_type;

  useEffect(() => {
    if (!isAwaitingScene || !sceneId) {
      setEventPackage(null);
      return;
    }
    if (pendingSceneType) {
      setEventPackage(isShortfallScene(pendingSceneType) ? formatShortfallEvent(sceneId, world) : null);
      return;
    }
    if (!playthroughId) {
      setEventPackage(null);
      return;
    }
    let isMounted = true;
    getSceneView(playthroughId, sceneId)
      .then((scene) => {
        if (!isMounted) return;
        setEventPackage(isShortfallScene(scene.scene_type) ? formatShortfallEvent(sceneId, world) : null);
      })
      .catch(() => {
        if (isMounted) setEventPackage(null);
      });
    return () => {
      isMounted = false;
    };
  }, [playthroughId, world, isAwaitingScene, sceneId, pendingSceneType]);

  const resolveChoice = useCallback(
    async (optionId: string): Promise<void> => {
      const targetSceneId = sceneId ?? eventPackage?.sceneId;
      if (!playthroughId || !targetSceneId || !world || !isEconomyChoice(optionId)) return;

      setIsResolving(true);
      try {
        await chooseEconomyOutcome(
          playthroughId,
          targetSceneId,
          optionId,
          buildOperationGuard(world),
        );
        await queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) });
        onResolved?.();
      } finally {
        setIsResolving(false);
      }
    },
    [playthroughId, sceneId, eventPackage?.sceneId, world, queryClient, onResolved],
  );

  return { eventPackage, isResolving, resolveChoice };
}
