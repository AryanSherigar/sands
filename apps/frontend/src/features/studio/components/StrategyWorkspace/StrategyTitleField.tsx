import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Input } from "@/shared/components/ui/Input";
import { updateScenario } from "../../api/scenarios.api";
import { TITLE_MAX_LENGTH } from "../../constants/guideLimits";
import { SCENARIO_QUERY_KEY } from "../../constants/studioScenario";
import type { StrategyTitleFieldProps } from "./StrategyWorkspace.types";

export const StrategyTitleField: React.FC<StrategyTitleFieldProps> = ({ scenario }) => {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(scenario.title);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleBlur = async (): Promise<void> => {
    const trimmed = title.trim();
    if (!trimmed || trimmed === scenario.title) return;
    try {
      const saved = await updateScenario(scenario.scenario_id, { title: trimmed });
      queryClient.setQueryData([SCENARIO_QUERY_KEY, scenario.scenario_id], saved);
      setErrorMessage(null);
    } catch {
      setErrorMessage("Couldn't save the title. Try again.");
    }
  };

  return (
    <label className="block space-y-1 text-sm">
      <span className="text-content-muted">Scenario title</span>
      <Input
        value={title}
        maxLength={TITLE_MAX_LENGTH}
        onChange={(event) => setTitle(event.target.value)}
        onBlur={handleBlur}
        error={errorMessage ?? undefined}
      />
    </label>
  );
};
