import { useEffect, useRef } from "react";
import type { CampaignWorldView } from "../types/simulation.types";
import { useBattleSpeech } from "./useBattleSpeech";

type WorldBattle = NonNullable<CampaignWorldView["battles"]>[number];

const isPlayerBattleInProgress = (battle: WorldBattle) =>
  battle.control_mode === "player" && battle.status !== "resolved";

export function useResumePendingBattleSpeech(
  playthroughId: string | undefined,
  battles: CampaignWorldView["battles"] | undefined,
  activeBattleId: string | null,
  onResume: (battleId: string) => void,
) {
  const candidateId = activeBattleId
    ? null
    : (battles?.find(isPlayerBattleInProgress)?.id ?? null);
  const { speech } = useBattleSpeech(playthroughId, candidateId);
  const resumedBattleId = useRef<string | null>(null);

  useEffect(() => {
    if (!candidateId || speech?.status !== "pending") return;
    if (resumedBattleId.current === candidateId) return;
    resumedBattleId.current = candidateId;
    onResume(candidateId);
  }, [candidateId, speech?.status, onResume]);
}
