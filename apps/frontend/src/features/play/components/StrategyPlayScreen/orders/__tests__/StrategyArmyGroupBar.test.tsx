import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyArmyGroupBar } from "../StrategyArmyGroupBar";

describe("StrategyArmyGroupBar", () => {
  it("renders nothing without a group", () => {
    const { container } = render(
      <StrategyArmyGroupBar count={0} isTargeting={false} onMove={vi.fn()} onHalt={vi.fn()} onMerge={vi.fn()} onClear={vi.fn()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("offers group move, halt and clear", () => {
    const handlers = { onMove: vi.fn(), onHalt: vi.fn(), onMerge: vi.fn(), onClear: vi.fn() };
    render(<StrategyArmyGroupBar count={3} isTargeting={false} {...handlers} />);

    expect(screen.getByText(/3 armies grouped/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Move group" }));
    fireEvent.click(screen.getByRole("button", { name: "Halt group" }));
    fireEvent.click(screen.getByRole("button", { name: "Merge group" }));
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));

    expect(handlers.onMerge).toHaveBeenCalledTimes(1);
    expect(handlers.onMove).toHaveBeenCalledTimes(1);
    expect(handlers.onHalt).toHaveBeenCalledTimes(1);
    expect(handlers.onClear).toHaveBeenCalledTimes(1);
  });

  it("cannot merge a single army", () => {
    render(<StrategyArmyGroupBar count={1} isTargeting={false} onMove={vi.fn()} onHalt={vi.fn()} onMerge={vi.fn()} onClear={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Merge group" })).toBeDisabled();
  });
});
