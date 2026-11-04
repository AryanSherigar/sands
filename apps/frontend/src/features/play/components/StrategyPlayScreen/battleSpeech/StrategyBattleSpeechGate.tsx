import { useBattleSpeech } from "../../../hooks/useBattleSpeech";
import { useBattleSpeechStore } from "../../../stores/battleSpeech.store";
import { StrategyBattleSpeechOverlay } from "./StrategyBattleSpeechOverlay";
import type { StrategyBattleSpeechGateProps } from "./StrategyBattleSpeechGate.types";

export function StrategyBattleSpeechGate({
  playthroughId,
  battleId,
  children,
}: StrategyBattleSpeechGateProps) {
  const { speech, isLoading } = useBattleSpeech(playthroughId, battleId);
  const phase = useBattleSpeechStore((state) => state.phase);

  if (isLoading) return null;
  const isSceneOpen = speech?.status === "pending" || phase === "reacting" || phase === "result";
  if (!isSceneOpen) return <>{children}</>;
  return <StrategyBattleSpeechOverlay playthroughId={playthroughId} battleId={battleId} />;
}
