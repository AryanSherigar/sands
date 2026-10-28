import type { ScenarioSummaryResponse } from "@/features/play/types/scenario";

export type CreationsFilter = "published" | "drafts";

export const filterCreations = (
  items: ScenarioSummaryResponse[],
  isOwner: boolean,
  filter: CreationsFilter,
): ScenarioSummaryResponse[] => {
  const isDraftView = isOwner && filter === "drafts";
  return items.filter((scenario) =>
    isDraftView
      ? scenario.status !== "published"
      : scenario.status === "published",
  );
};
