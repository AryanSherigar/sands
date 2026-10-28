import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { ADVANCED_GUIDE_STEPS } from "../../constants/advancedSteps";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderGuideStep } from "../../test/renderGuideStep";
import { StepEndings } from "./StepEndings";
import { StepHardLimits } from "./StepHardLimits";
import { StepRules } from "./StepRules";
import { StepTrackedValues } from "./StepTrackedValues";

const CASES = [
  { id: "endings", Step: StepEndings, example: /Lose ending: The Tide Takes Her/ },
  { id: "tracked_values", Step: StepTrackedValues, example: /Tide time: 0 to 60/ },
  { id: "rules", Step: StepRules, example: /When Tide time is at most 10/ },
  { id: "hard_limits", Step: StepHardLimits, example: /While Door open is yes/ },
] as const;

describe("Advanced Guide steps", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  it.each(CASES)("$id shows its question, helper and the demo story example", async ({ id, Step, example }) => {
    const definition = ADVANCED_GUIDE_STEPS.find((step) => step.id === id);
    const { user } = await renderGuideStep(<Step />);
    expect(await screen.findByRole("heading", { name: definition?.header })).toBeInTheDocument();
    expect(screen.getByText(definition?.helper ?? "")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show an example" }));
    expect(screen.getByRole("complementary", { name: "Example" })).toHaveTextContent(example);
  });
});
