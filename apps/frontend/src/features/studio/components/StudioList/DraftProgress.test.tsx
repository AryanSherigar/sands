import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { STUDIO_TABS_STORAGE_PREFIX } from "../../constants/studioTabs";
import type { MyScenarioSummary } from "../../types/scenario.types";
import { DraftProgress } from "./DraftProgress";

const buildSummary = (overrides: Partial<MyScenarioSummary>): MyScenarioSummary =>
  ({ scenario_id: "draft-1", title: "T", logline: "L", mode: "newbie", ...overrides }) as MyScenarioSummary;

const remember = (stepNumber: number): void =>
  localStorage.setItem(`${STUDIO_TABS_STORAGE_PREFIX}draft-1`, JSON.stringify({ guideStep: stepNumber }));

describe("DraftProgress", () => {
  beforeEach(() => localStorage.clear());

  it("reads the remembered step against the story's own step count", () => {
    remember(9);
    render(<DraftProgress scenario={buildSummary({ mode: "master" })} />);

    expect(screen.getByText("Step 9 of 12 · Rules")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "9");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "12");
  });

  it("falls back to Opening when the remembered step belongs to Advanced mode that is now off", () => {
    remember(9);
    render(<DraftProgress scenario={buildSummary({ mode: "newbie" })} />);

    expect(screen.getByText("Step 6 of 7 · Opening")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar");
    expect(Number(bar.getAttribute("aria-valuenow"))).toBeLessThanOrEqual(Number(bar.getAttribute("aria-valuemax")));
  });
});
