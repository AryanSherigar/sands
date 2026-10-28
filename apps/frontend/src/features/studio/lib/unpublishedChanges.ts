import type { ScenarioResponse } from "../types/scenario.types";

type PublishStamps = Pick<ScenarioResponse, "status" | "content_edited_at" | "published_at">;

export const hasServerUnpublishedChanges = (scenario: PublishStamps | null): boolean => {
  if (!scenario || scenario.status !== "published") return false;
  if (!scenario.content_edited_at || !scenario.published_at) return false;
  return new Date(scenario.content_edited_at).getTime() > new Date(scenario.published_at).getTime();
};

export const countUnpublishedChanges = (
  sessionEditCount: number,
  hasServerChanges: boolean,
): number => {
  if (sessionEditCount > 0) return sessionEditCount;
  return hasServerChanges ? 1 : 0;
};

export const describeLiveStatus = (changeCount: number): string => {
  if (changeCount === 0) return "Live";
  const noun = changeCount === 1 ? "change" : "changes";
  return `Live · ${changeCount} unpublished ${noun}`;
};
