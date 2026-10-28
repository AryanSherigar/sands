import React from "react";
import { useNavigate } from "react-router-dom";
import { OverflowMenu } from "@/shared/components/ui/OverflowMenu";
import { STUDIO_LIST_PATH } from "../../constants/studioFrame";
import { useArchiveScenario } from "../../hooks/useArchiveScenario";
import { useDuplicateScenario } from "../../hooks/useDuplicateScenario";
import { STATS_VISIBLE_STATUSES } from "../../constants/stats";
import { useGuide } from "../../hooks/useGuide";
import { useOpenFullEditor } from "../../hooks/useOpenFullEditor";
import type { OverflowMenuItem } from "@/shared/components/ui/OverflowMenu.types";

const NO_SCENARIO_ID = "";

export const StoryMenu: React.FC = () => {
  const navigate = useNavigate();
  const { scenarioId, scenario } = useGuide();
  const openFullEditor = useOpenFullEditor();
  const { duplicate } = useDuplicateScenario(scenarioId ?? NO_SCENARIO_ID);
  const { archive } = useArchiveScenario(scenarioId);
  if (!scenarioId) return null;

  const handleDuplicate = (): void =>
    duplicate(undefined, {
      onSuccess: (copy) => navigate(`/studio/${copy.scenario_id}/edit`),
    });
  const handleArchive = (): void =>
    archive(undefined, { onSuccess: () => navigate(STUDIO_LIST_PATH) });

  const items: OverflowMenuItem[] = [];
  if (scenario?.mode === "master") {
    items.push({ id: "full-editor", label: "Open full editor", onSelect: openFullEditor });
  }
  if (scenario && STATS_VISIBLE_STATUSES.includes(scenario.status)) {
    items.push({ id: "stats", label: "View stats", onSelect: () => navigate(`/studio/${scenarioId}/stats`) });
  }
  items.push(
    { id: "duplicate", label: "Duplicate story", onSelect: handleDuplicate },
    { id: "archive", label: "Archive", onSelect: handleArchive, isDanger: true },
  );

  return <OverflowMenu label="Story options" items={items} />;
};
