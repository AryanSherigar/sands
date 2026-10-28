import React from "react";
import { useGuide } from "../../hooks/useGuide";
import { useSyncedValue } from "../../hooks/useSyncedValue";
import type { ScenarioResponse } from "../../types/scenario.types";

type PlayerMode = NonNullable<ScenarioResponse["player_mode"]>;

const OPTIONS: Array<{ value: PlayerMode; label: string }> = [
  { value: "written", label: "A character I write" },
  { value: "player_created", label: "Someone the player creates" },
];

export const PlayerModeChoice: React.FC = () => {
  const { scenario, saveFields } = useGuide();
  const { value: playerMode, commit } = useSyncedValue<PlayerMode>(
    scenario?.player_mode ?? "written",
    (next) => saveFields({ player_mode: next }),
  );

  return (
    <fieldset className="space-y-2">
      <legend className="sr-only">Who will the player be?</legend>
      {OPTIONS.map((option) => (
        <label
          key={option.value}
          className="flex cursor-pointer items-center gap-3 rounded-md border border-border-subtle bg-surface-raised px-4 py-3 text-body text-content has-checked:border-primary"
        >
          <input
            type="radio"
            name="player-mode"
            value={option.value}
            checked={playerMode === option.value}
            onChange={() => commit(option.value)}
            className="accent-primary"
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
};
