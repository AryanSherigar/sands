import React, { useState } from "react";
import { MOOD_CHIPS } from "../../constants/guideChips";
import { MAX_MOOD_TAG_LENGTH } from "../../constants/guideLimits";
import { useGuide } from "../../hooks/useGuide";
import { useSyncedValue } from "../../hooks/useSyncedValue";
import { addCustomMood, toggleTag } from "../../lib/guideTags";
import { GuideChip } from "./GuideChip";

const EMPTY_TAGS: string[] = [];

export const MoodChips: React.FC = () => {
  const { scenario, saveFields } = useGuide();
  const [customMood, setCustomMood] = useState("");
  const { value: selected, commit } = useSyncedValue(
    scenario?.mood_tags ?? EMPTY_TAGS,
    (next) => saveFields({ mood_tags: next }),
  );
  const customSelected = selected.filter(
    (mood) => !(MOOD_CHIPS as readonly string[]).includes(mood),
  );

  const handleCustomKeyDown = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    commit(addCustomMood(selected, customMood));
    setCustomMood("");
  };

  return (
    <div role="group" aria-labelledby="mood-chips-label" className="space-y-2">
      <p id="mood-chips-label" className="text-meta font-medium text-content-muted">
        How should it feel?
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {[...MOOD_CHIPS, ...customSelected].map((mood) => (
          <GuideChip
            key={mood}
            label={mood}
            isSelected={selected.includes(mood)}
            onClick={() => commit(toggleTag(selected, mood))}
          />
        ))}
        <input
          type="text"
          aria-label="Add your own feeling"
          placeholder="+ your own"
          value={customMood}
          maxLength={MAX_MOOD_TAG_LENGTH}
          onChange={(event) => setCustomMood(event.target.value)}
          onKeyDown={handleCustomKeyDown}
          className="h-8 w-32 rounded-sm border border-border-strong bg-surface-inset px-2 text-meta text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden"
        />
      </div>
    </div>
  );
};
