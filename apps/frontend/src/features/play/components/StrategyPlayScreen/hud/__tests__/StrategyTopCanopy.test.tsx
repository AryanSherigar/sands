import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyTopCanopy } from "../StrategyTopCanopy";
import type { CampaignWorldView } from "../../../../types/simulation.types";

const mockWorld: CampaignWorldView = {
  world_version: 1,
  turn: 1,
  wave: 0,
  status: "planning",
  battles: [],
  clock: { turn: 1, start_year: 1042, start_month: 7 },
  my_faction: {
    id: "f1",
    treasury: 340,
    manpower: 14200,
    stability: 2,
    war_exhaustion: 0,
    reputation: 50,
    tax_rate: "normal",
    loans: [],
  },
  ruler: { name: "King Alden IV" },
  regions: [],
  armies: [],
  rivals: [],
  queued_orders: [],
  orders_remaining: 4,
};

describe("StrategyTopCanopy", () => {
  it("renders ruler name and core stats", () => {
    render(<StrategyTopCanopy world={mockWorld} />);
    expect(screen.getByText("King Alden IV")).toBeInTheDocument();
    expect(screen.getByText("340")).toBeInTheDocument();
    expect(screen.getByText("14,200")).toBeInTheDocument();
    expect(screen.getByText("4 / 4 Remaining")).toBeInTheDocument();
  });

  it("handles map mode switching", () => {
    const onSelect = vi.fn();
    render(
      <StrategyTopCanopy
        world={mockWorld}
        activeMapMode="political"
        onSelectMapMode={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("terrain"));
    expect(onSelect).toHaveBeenCalledWith("terrain");
  });

  it("renders default sovereign fallback when world is undefined", () => {
    render(<StrategyTopCanopy />);
    expect(screen.getByText("Sovereign")).toBeInTheDocument();
    expect(screen.getByText("Crown of the Realm")).toBeInTheDocument();
    expect(screen.getByText("0 / 0 Remaining")).toBeInTheDocument();
  });

  it("renders active crises button when activeCrisesCount > 0 and calls onToggleSituations", () => {
    const onToggle = vi.fn();
    const { rerender } = render(
      <StrategyTopCanopy
        world={mockWorld}
        activeCrisesCount={1}
        onToggleSituations={onToggle}
      />,
    );

    const button = screen.getByRole("button", { name: /1 active crisis/i });
    expect(button).toBeInTheDocument();
    fireEvent.click(button);
    expect(onToggle).toHaveBeenCalledTimes(1);

    rerender(
      <StrategyTopCanopy
        world={mockWorld}
        activeCrisesCount={3}
        onToggleSituations={onToggle}
      />,
    );
    expect(
      screen.getByRole("button", { name: /3 active crises/i }),
    ).toBeInTheDocument();
  });

  it("does not render active crises button when activeCrisesCount is 0 or omitted", () => {
    render(<StrategyTopCanopy world={mockWorld} activeCrisesCount={0} />);
    expect(screen.queryByRole("button", { name: /active cris/i })).toBeNull();
  });
});
