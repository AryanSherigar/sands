import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyHistoryScrubber } from "../StrategyHistoryScrubber";

const props = { latestTurn: 5, viewedTurn: 3, isLoading: false, hasFailed: false };

describe("StrategyHistoryScrubber", () => {
  it("steps and scrubs between turns and returns to the present", () => {
    const onChangeTurn = vi.fn();
    const onReturnToPresent = vi.fn();
    render(<StrategyHistoryScrubber {...props} onChangeTurn={onChangeTurn} onReturnToPresent={onReturnToPresent} />);

    expect(screen.getByText(/Turn 3 of 5/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Earlier turn" }));
    fireEvent.click(screen.getByRole("button", { name: "Later turn" }));
    fireEvent.change(screen.getByRole("slider", { name: "Turn" }), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Return to the present" }));

    expect(onChangeTurn).toHaveBeenNthCalledWith(1, 2);
    expect(onChangeTurn).toHaveBeenNthCalledWith(2, 4);
    expect(onChangeTurn).toHaveBeenNthCalledWith(3, 1);
    expect(onReturnToPresent).toHaveBeenCalledTimes(1);
  });

  it("stops at the ends and reports loading and failure", () => {
    const { rerender } = render(
      <StrategyHistoryScrubber {...props} viewedTurn={0} isLoading onChangeTurn={vi.fn()} onReturnToPresent={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Earlier turn" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Unrolling");

    rerender(<StrategyHistoryScrubber {...props} viewedTurn={5} hasFailed onChangeTurn={vi.fn()} onReturnToPresent={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Later turn" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
