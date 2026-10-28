import { STUDIO_TABS_STORAGE_PREFIX } from "../constants/studioTabs";
import { logEvent } from "@/shared/lib/logger";
import type { MyScenarioSummary } from "../types/scenario.types";
import { clampGuideStep, getGuideStepCount, getGuideSteps } from "./guideStepsFor";

const FIRST_STEP = 1;
const IDEA_DONE_NEXT_STEP = 2;

const isValidStep = (value: unknown): value is number =>
  typeof value === "number" &&
  Number.isInteger(value) &&
  value >= FIRST_STEP &&
  value <= getGuideStepCount(true);

export const readRememberedGuideStep = (scenarioId: string): number | null => {
  try {
    const raw = localStorage.getItem(`${STUDIO_TABS_STORAGE_PREFIX}${scenarioId}`);
    if (raw === null) return null;
    const parsed: unknown = JSON.parse(raw);
    const step = (parsed as { guideStep?: unknown } | null)?.guideStep;
    return isValidStep(step) ? step : null;
  } catch (error) {
    logEvent("warning", "draft_progress_read_failed", { message: String(error) });
    return null;
  }
};

export const getDraftGuideStep = (
  scenario: Pick<MyScenarioSummary, "title" | "logline">,
  rememberedStep: number | null,
): number => {
  if (rememberedStep !== null) return rememberedStep;
  const hasIdea = Boolean(scenario.title.trim() && scenario.logline?.trim());
  return hasIdea ? IDEA_DONE_NEXT_STEP : FIRST_STEP;
};

export const formatDraftProgress = (stepNumber: number, isAdvanced: boolean): string => {
  const steps = getGuideSteps(isAdvanced);
  const step = steps[clampGuideStep(stepNumber, isAdvanced) - 1];
  return `Step ${step.number} of ${steps.length} · ${step.name}`;
};
