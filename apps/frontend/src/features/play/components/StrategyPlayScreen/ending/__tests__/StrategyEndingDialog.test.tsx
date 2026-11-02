import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyEndingDialog } from "../StrategyEndingDialog";

const ENDING = {
  ending_id: "default_graded_end_date",
  kind: "graded",
  turn: 40,
  grade: "honorable" as const,
  inputs: { position: 62, stability: 48, treasury: 130 },
};

describe("StrategyEndingDialog", () => {
  it("shows the ending, its grade and the clamped inputs", () => {
    render(<StrategyEndingDialog ending={ENDING} isOpen onReviewRealm={vi.fn()} onLeave={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: "The Campaign Ends" })).toBeInTheDocument();
    expect(screen.getByText("Honorable")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Land held" })).toHaveAttribute("aria-valuenow", "62");
    expect(screen.getByRole("meter", { name: "Treasury" })).toHaveAttribute("aria-valuenow", "100");
  });

  it("lets the player look over the realm (also on Escape) or leave", () => {
    const handlers = { onReviewRealm: vi.fn(), onLeave: vi.fn() };
    render(<StrategyEndingDialog ending={ENDING} isOpen {...handlers} />);

    fireEvent.click(screen.getByRole("button", { name: "Look over the realm" }));
    fireEvent.keyDown(document, { key: "Escape" });
    fireEvent.click(screen.getByRole("button", { name: "Leave the campaign" }));

    expect(handlers.onReviewRealm).toHaveBeenCalledTimes(2);
    expect(handlers.onLeave).toHaveBeenCalledTimes(1);
  });

  it("renders nothing while the realm is being reviewed", () => {
    const { container } = render(
      <StrategyEndingDialog ending={ENDING} isOpen={false} onReviewRealm={vi.fn()} onLeave={vi.fn()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
