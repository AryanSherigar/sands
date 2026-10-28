import type { MyScenarioSummary } from "../types/scenario.types";

export type DisplayStatus =
  | "draft"
  | "publishing"
  | "published"
  | "published_changes"
  | "publish_failed"
  | "archived";

export const getDisplayStatus = (scenario: MyScenarioSummary): DisplayStatus => {
  if (scenario.status === "draft" && scenario.publish_error) {
    return "publish_failed";
  }
  if (scenario.status === "published" && scenario.has_unpublished_changes) {
    return "published_changes";
  }
  return scenario.status;
};

export const isLiveStatus = (status: DisplayStatus): boolean =>
  status === "published" || status === "published_changes";

const EVER_PUBLISHED_STATUSES: MyScenarioSummary["status"][] = [
  "published",
  "publish_failed",
];

export const getDeleteOutcome = (
  scenario: MyScenarioSummary,
): "deleted" | "archived" =>
  EVER_PUBLISHED_STATUSES.includes(scenario.status) ? "archived" : "deleted";

export const isTitleConfirmed = (
  typed: string,
  title: string,
  fallback: string,
): boolean =>
  typed.trim().toLowerCase() === (title.trim() || fallback).toLowerCase();
