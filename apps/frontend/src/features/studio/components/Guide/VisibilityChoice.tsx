import React from "react";
import { useGuide } from "../../hooks/useGuide";
import { useSyncedValue } from "../../hooks/useSyncedValue";
import type { ScenarioVisibility } from "@/shared/types/scenarioSummary.types";
import { InvitePeoplePanel } from "../PublishSuccess/InvitePeoplePanel";

const OPTIONS: Array<{ value: ScenarioVisibility; label: string }> = [
  { value: "private", label: "Only people I invite" },
  { value: "public", label: "Everyone" },
];

export const VisibilityChoice: React.FC = () => {
  const { scenarioId, scenario, saveFields } = useGuide();
  const { value: visibility, commit } = useSyncedValue<ScenarioVisibility>(
    scenario?.visibility ?? "private",
    (next) => saveFields({ visibility: next }),
  );

  return (
    <fieldset className="space-y-2">
      <legend className="text-meta font-medium text-content-muted">Who can play it?</legend>
      {OPTIONS.map((option) => (
        <label
          key={option.value}
          className="flex cursor-pointer items-center gap-3 rounded-md border border-border-subtle bg-surface-raised px-4 py-3 text-body text-content has-checked:border-primary"
        >
          <input
            type="radio"
            name="story-visibility"
            value={option.value}
            checked={visibility === option.value}
            onChange={() => commit(option.value)}
            className="accent-primary"
          />
          {option.label}
        </label>
      ))}
      {visibility === "private" && scenarioId && <InvitePeoplePanel scenarioId={scenarioId} />}
    </fieldset>
  );
};
