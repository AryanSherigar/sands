import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyEndingOverlay } from "../StrategyEndingOverlay";
import type { EndingView } from "../../../../types/simulation.types";

const triumph: EndingView = {
  ending_id: "default_graded_end_date",
  kind: "graded",
  turn: 29,
  grade: "triumph",
};

function renderOverlay(ending: EndingView, handlers = {}) {
  const props = {
    ending,
    onReadLegacy: vi.fn(),
    onReturnToScenario: vi.fn(),
    onReplay: vi.fn(),
    ...handlers,
  };
  render(<StrategyEndingOverlay {...props} />);
  return props;
}

describe("StrategyEndingOverlay", () => {
  it("shows the tier word and the ending title and no numbers", () => {
    renderOverlay(triumph);
    expect(screen.getByText("Triumph")).toBeInTheDocument();
    expect(screen.getByText("The Reign Reaches Its End")).toBeInTheDocument();
    const dialog = screen.getByRole("dialog");
    expect(dialog.textContent).not.toMatch(/\d/);
  });

  it("labels a pyrrhic grade as a Pyrrhic Victory", () => {
    renderOverlay({ ...triumph, grade: "pyrrhic" });
    expect(screen.getByText("Pyrrhic Victory")).toBeInTheDocument();
  });

  it("falls back to Ruin for a defeat without a grade", () => {
    renderOverlay({ ending_id: "default_defeat_capital_lost", kind: "defeat", turn: 2 });
    expect(screen.getByText("Ruin")).toBeInTheDocument();
    expect(screen.getByText("The Capital Falls")).toBeInTheDocument();
  });

  it("shows the vassal outcome by its ending title", () => {
    renderOverlay({ ending_id: "default_graded_vassal_state", kind: "graded", turn: 29, grade: "bitter" });
    expect(screen.getByText("A Vassal's Crown")).toBeInTheDocument();
  });

  it("uses a generic title for an unknown ending", () => {
    renderOverlay({ ending_id: "creator_made_up", kind: "victory", turn: 5 });
    expect(screen.getByText("The Reign Ends")).toBeInTheDocument();
    expect(screen.getByText("Triumph")).toBeInTheDocument();
  });

  it("calls the matching handler for each exit", () => {
    const handlers = renderOverlay(triumph);
    fireEvent.click(screen.getByRole("button", { name: "Read the legacy" }));
    fireEvent.click(screen.getByRole("button", { name: "Return to the scenario page" }));
    fireEvent.click(screen.getByRole("button", { name: "Replay" }));
    expect(handlers.onReadLegacy).toHaveBeenCalledTimes(1);
    expect(handlers.onReturnToScenario).toHaveBeenCalledTimes(1);
    expect(handlers.onReplay).toHaveBeenCalledTimes(1);
  });

  it("shows the name the author gave a creator-defined ending", () => {
    renderOverlay({ ending_id: "golden_age", kind: "victory", turn: 9, name: "The Golden Age" });

    expect(screen.getByText("The Golden Age")).toBeInTheDocument();
  });
});
