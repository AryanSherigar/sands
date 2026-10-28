import React from "react";
import { StrategyFactionsSection } from "../components/StrategyWorkspace/StrategyFactionsSection";
import { StrategyMapSection } from "../components/StrategyWorkspace/StrategyMapSection";
import { StrategyPublishSection } from "../components/StrategyWorkspace/StrategyPublishSection";
import { StrategyStartSection } from "../components/StrategyWorkspace/StrategyStartSection";
import { StrategyTitleField } from "../components/StrategyWorkspace/StrategyTitleField";
import { useStrategyCheck } from "../hooks/useStrategyCheck";
import { useStrategyFields } from "../hooks/useStrategyFields";
import { useStrategyMap } from "../hooks/useStrategyMap";
import type { ScenarioResponse } from "../types/scenario.types";

const SAVE_LABELS = { saved: "All changes saved", saving: "Saving…", failed: "Couldn't save. Keep editing to retry." };

interface StrategyWorkspacePageProps {
  scenario: ScenarioResponse;
}

export const StrategyWorkspacePage: React.FC<StrategyWorkspacePageProps> = ({ scenario }) => {
  const { fields, edit, flush, saveState } = useStrategyFields(scenario);
  const { data: map, isLoading: isMapLoading } = useStrategyMap(scenario.scenario_id);
  const check = useStrategyCheck(scenario.scenario_id, scenario.content_edited_at);
  const regions = map?.regions ?? [];

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-6 font-sans text-content">
      <header className="flex items-end justify-between gap-4">
        <h1 className="text-2xl font-semibold">Strategy scenario</h1>
        <p role="status" className="text-xs text-content-muted">{SAVE_LABELS[saveState]}</p>
      </header>
      <StrategyTitleField scenario={scenario} />
      <StrategyMapSection scenarioId={scenario.scenario_id} />
      <StrategyFactionsSection fields={fields} regions={regions} onEdit={edit} />
      <StrategyStartSection fields={fields} regions={regions} onEdit={edit} />
      <StrategyPublishSection
        scenario={scenario}
        report={check.data}
        isMapMissing={!isMapLoading && regions.length === 0}
        onFlush={flush}
      />
    </main>
  );
};
