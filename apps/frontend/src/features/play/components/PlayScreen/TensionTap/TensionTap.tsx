import { useEffect, useState } from "react";
import { useAlphaConfig } from "@/shared/hooks/useAlphaConfig";
import { emitAlphaEvent } from "@/shared/lib/alpha-events";
import { TENSION_RATINGS } from "../../../constants/alpha-feedback.constants";
import { usePlayStore } from "../../../stores/play.store";

const PROMPT_LABEL = "How tense was that stretch? (1 calm, 5 unbearable)";

function selectIsBusy(state: ReturnType<typeof usePlayStore.getState>): boolean {
  return (
    state.is_narrating ||
    state.is_check_animation_pending ||
    state.active_minigame !== null ||
    state.active_check !== null ||
    state.active_rule_check !== null ||
    Boolean(state.playthrough?.ended_outcome_tag)
  );
}

export function TensionTap() {
  const { data: config } = useAlphaConfig();
  const every = config?.is_alpha_mode ? config.tension_prompt_every_turns : null;
  const playthroughId = usePlayStore((s) => s.playthrough?.playthrough_id);
  const turnCount = usePlayStore((s) => s.playthrough?.turns.length ?? 0);
  const isBusy = usePlayStore(selectIsBusy);
  const [lastPromptedTurn, setLastPromptedTurn] = useState<number | null>(null);

  useEffect(() => {
    if (lastPromptedTurn !== null || !playthroughId || !every) return;
    setLastPromptedTurn(turnCount - (turnCount % every));
  }, [lastPromptedTurn, playthroughId, every, turnCount]);

  if (!every || !playthroughId || lastPromptedTurn === null || isBusy) return null;
  if (turnCount - lastPromptedTurn < every) return null;

  const handleRate = (rating: number): void => {
    emitAlphaEvent(
      "tension_rating",
      { turn_number: turnCount, rating },
      { playthroughId },
    );
    setLastPromptedTurn(turnCount);
  };

  return (
    <div
      role="group"
      aria-label={PROMPT_LABEL}
      className="fixed bottom-24 left-1/2 z-30 w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 rounded-xl border border-border-strong bg-surface-overlay p-3 shadow-float"
    >
      <p className="mb-2 text-center font-mono text-xs text-content-muted">{PROMPT_LABEL}</p>
      <div className="flex justify-center gap-2">
        {TENSION_RATINGS.map((rating) => (
          <button
            key={rating}
            type="button"
            onClick={() => handleRate(rating)}
            className="min-h-11 min-w-11 rounded-md border border-border-strong bg-surface-raised font-mono text-sm text-content hover:bg-surface-overlay cursor-pointer"
          >
            {rating}
          </button>
        ))}
      </div>
    </div>
  );
}
