import type {
  MinigameEventPayload,
  MinigameOutcomeTag,
} from "@/shared/types/minigame.types";

const FALLBACK_WIN = "You finish.";
const FALLBACK_STOP = "You stop.";

interface ResultTexts {
  win_text: string;
  lose_text: string;
}

function configTexts(minigame: MinigameEventPayload): ResultTexts | undefined {
  return (
    minigame.composure_config?.texts ??
    minigame.lockpick_config?.copy ??
    minigame.dodge_config?.copy
  );
}

/** What the turn history shows as the player's action for a minigame result. */
export function minigameActionText(
  minigame: MinigameEventPayload | null,
  outcome: MinigameOutcomeTag,
): string {
  const texts = minigame ? configTexts(minigame) : undefined;
  if (outcome === "win") return texts?.win_text || FALLBACK_WIN;
  return texts?.lose_text || FALLBACK_STOP;
}
