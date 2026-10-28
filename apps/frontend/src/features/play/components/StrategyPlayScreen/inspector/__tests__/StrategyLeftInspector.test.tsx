import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyLeftInspector } from "../StrategyLeftInspector";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import type { ArmyView, CampaignWorldView } from "../../../../types/simulation.types";

const mockRegion: MapRegion = {
  id: "reg-1",
  name: "Dunmere Vale",
  terrain: "plain",
  outline: "",
  label_point: { x: 0, y: 0 },
  neighbor_ids: [],
  source_color: null,
  source_ref: null,
};

const mockArmy: ArmyView = {
  army_id: "army-1",
  owner_id: "faction-1",
  location_id: "reg-1",
  commander_name: "Lord Aethelgard",
  troops: { infantry: 1200 },
};

const mockWorld: CampaignWorldView = {
  world_version: 1,
  turn: 1,
  wave: 0,
  status: "planning",
  battles: [],
  clock: { turn: 1, start_year: 1042, start_month: 7 },
  my_faction: {
    id: "faction-1",
    treasury: 100,
    manpower: 100,
    stability: 50,
    war_exhaustion: 0,
    reputation: 0,
    tax_rate: "normal",
    loans: [],
  },
  ruler: { name: "King" },
  regions: [{ region_id: "reg-1", owner_id: "faction-1", terrain: "plain", visibility: "visible" }],
  armies: [mockArmy],
  rivals: [],
  queued_orders: [],
  orders_remaining: 3,
};

describe("StrategyLeftInspector", () => {
  it("is hidden when selectedEntity is null", () => {
    const { container } = render(
      <StrategyLeftInspector selectedEntity={null} onClose={vi.fn()} />,
    );
    expect(container.firstChild).toHaveClass("-translate-x-[110%]");
  });

  it("renders province charter when a region is selected", () => {
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("Dunmere Vale")).toBeInTheDocument();
    expect(screen.getByText("Provincial Charter")).toBeInTheDocument();
  });

  it("renders army roster when an army is selected", () => {
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "army", id: "army-1" }}
        army={mockArmy}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("Command Host")).toBeInTheDocument();
    expect(screen.getByText("Lord Aethelgard")).toBeInTheDocument();
    expect(screen.getByText("1,200")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const handleClose = vi.fn();
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        onClose={handleClose}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Close inspector" }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("dispatches actions from province charter", () => {
    const handleAction = vi.fn();
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={mockWorld}
        onClose={vi.fn()}
        onAction={handleAction}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Levy Troops" }));
    expect(handleAction).toHaveBeenCalledWith({ type: "levy", regionId: "reg-1" });
  });

  it("hides levy for regions the player does not own", () => {
    const rivalWorld = {
      ...mockWorld,
      regions: [{ ...mockWorld.regions[0], owner_id: "faction-2" }],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={rivalWorld}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Levy Troops" })).not.toBeInTheDocument();
  });

  it("dispatches actions from army roster", () => {
    const handleAction = vi.fn();
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "army", id: "army-1" }}
        army={mockArmy}
        world={mockWorld}
        onClose={vi.fn()}
        onAction={handleAction}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Move" }));
    expect(handleAction).toHaveBeenCalledWith({ type: "move", armyId: "army-1" });

    fireEvent.click(screen.getByRole("button", { name: "Attack" }));
    expect(handleAction).toHaveBeenCalledWith({ type: "attack", armyId: "army-1" });

    fireEvent.click(screen.getByRole("button", { name: "Halt" }));
    expect(handleAction).toHaveBeenCalledWith({ type: "halt", armyId: "army-1" });
  });
});
