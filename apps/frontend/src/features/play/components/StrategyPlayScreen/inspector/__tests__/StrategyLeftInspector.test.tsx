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

  it("displays Unobserved for dynamic metrics when an unowned region is fogged", () => {
    const foggedWorld: CampaignWorldView = {
      ...mockWorld,
      regions: [
        {
          region_id: "reg-1",
          owner_id: "faction-2",
          terrain: "plain",
          visibility: "fogged",
          last_seen_turn: null,
          detail: {
            id: "reg-1",
            owner_id: "faction-2",
            population: 5000,
            wealth: 40,
            manpower: 800,
            unrest: 10,
            garrison: 200,
            faith_id: null,
            improvements: [],
            claimant_ids: [],
            conversion_turns_remaining: 0,
          },
        },
      ],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={foggedWorld}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getAllByText("Unobserved")).toHaveLength(4);
    expect(screen.queryByText("5,000")).not.toBeInTheDocument();
    expect(screen.queryByText("40g")).not.toBeInTheDocument();
    expect(screen.getByText("Dunmere Vale")).toBeInTheDocument();
  });

  it("displays Unobserved with last seen turn when last_seen_turn is present", () => {
    const foggedWorld: CampaignWorldView = {
      ...mockWorld,
      regions: [
        {
          region_id: "reg-1",
          owner_id: "faction-2",
          terrain: "plain",
          visibility: "fogged",
          last_seen_turn: 4,
        },
      ],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={foggedWorld}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getAllByText("Unobserved (T4)")).toHaveLength(4);
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

  it("renders Declare War and Send Envoy for foreign region at peace", () => {
    const handleAction = vi.fn();
    const foreignWorld: CampaignWorldView = {
      ...mockWorld,
      regions: [{ ...mockWorld.regions[0], owner_id: "faction-2" }],
      rivals: [
        {
          faction_id: "faction-2",
          name: "Dunmere",
          relation: "peace",
          treasury_range: { low: 10, high: 20 },
          manpower_range: { low: 100, high: 200 },
        },
      ],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={foreignWorld}
        onClose={vi.fn()}
        onAction={handleAction}
      />,
    );

    const declareWarBtn = screen.getByRole("button", { name: "Declare War" });
    const sendEnvoyBtn = screen.getByRole("button", { name: "Send Envoy" });
    expect(declareWarBtn).toBeInTheDocument();
    expect(declareWarBtn).not.toBeDisabled();
    expect(sendEnvoyBtn).toBeInTheDocument();

    fireEvent.click(declareWarBtn);
    expect(handleAction).toHaveBeenCalledWith({ type: "declare_war", targetFactionId: "faction-2" });

    fireEvent.click(sendEnvoyBtn);
    expect(handleAction).toHaveBeenCalledWith({ type: "send_envoy", targetFactionId: "faction-2" });
  });

  it("disables Declare War with truce label when truce is active", () => {
    const handleAction = vi.fn();
    const truceWorld: CampaignWorldView = {
      ...mockWorld,
      regions: [{ ...mockWorld.regions[0], owner_id: "faction-2" }],
      truces: [
        {
          faction_a: "faction-1",
          faction_b: "faction-2",
          expires_turn: 10,
          is_fragile: false,
          guarantor_ids: [],
        },
      ],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={truceWorld}
        onClose={vi.fn()}
        onAction={handleAction}
      />,
    );

    const declareWarBtn = screen.getByRole("button", { name: "Declare War" });
    expect(declareWarBtn).toBeDisabled();
    expect(screen.getByText("Truce active until turn 10")).toBeInTheDocument();

    fireEvent.click(declareWarBtn);
    expect(handleAction).not.toHaveBeenCalled();
  });

  it("renders Hostile Possession and Sue for Peace when at war", () => {
    const handleAction = vi.fn();
    const warWorld: CampaignWorldView = {
      ...mockWorld,
      regions: [{ ...mockWorld.regions[0], owner_id: "faction-2" }],
      rivals: [
        {
          faction_id: "faction-2",
          name: "Dunmere",
          relation: "at_war",
          treasury_range: { low: 10, high: 20 },
          manpower_range: { low: 100, high: 200 },
        },
      ],
      wars: [
        {
          id: "war-7",
          attacker_id: "faction-1",
          defender_id: "faction-2",
        },
      ],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={warWorld}
        onClose={vi.fn()}
        onAction={handleAction}
      />,
    );

    expect(screen.getByText("Hostile Possession")).toBeInTheDocument();
    const suePeaceBtn = screen.getByRole("button", { name: "Sue for Peace" });
    expect(suePeaceBtn).toBeInTheDocument();

    fireEvent.click(suePeaceBtn);
    expect(handleAction).toHaveBeenCalledWith({ type: "sue_peace", warId: "war-7" });
  });

  it("renders Declare War for foreign army when not at war", () => {
    const handleAction = vi.fn();
    const foreignArmy: ArmyView = {
      ...mockArmy,
      army_id: "army-foreign",
      owner_id: "faction-2",
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "army", id: "army-foreign" }}
        army={foreignArmy}
        world={mockWorld}
        onClose={vi.fn()}
        onAction={handleAction}
      />,
    );

    const declareWarBtn = screen.getByRole("button", { name: "Declare War" });
    expect(declareWarBtn).toBeInTheDocument();
    fireEvent.click(declareWarBtn);
    expect(handleAction).toHaveBeenCalledWith({ type: "declare_war", targetFactionId: "faction-2" });
  });

  it("does not render Declare War for foreign army when at war", () => {
    const foreignArmy: ArmyView = {
      ...mockArmy,
      army_id: "army-foreign",
      owner_id: "faction-2",
    };
    const warWorld: CampaignWorldView = {
      ...mockWorld,
      rivals: [
        {
          faction_id: "faction-2",
          name: "Dunmere",
          relation: "war",
          treasury_range: { low: 10, high: 20 },
          manpower_range: { low: 100, high: 200 },
        },
      ],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "army", id: "army-foreign" }}
        army={foreignArmy}
        world={warWorld}
        onClose={vi.fn()}
        onAction={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Declare War" })).not.toBeInTheDocument();
  });

  it("shows who occupies the selected region", () => {
    const world: CampaignWorldView = {
      ...mockWorld,
      rivals: [{ faction_id: "faction-2", name: "House Carrow", relation: "war" }] as CampaignWorldView["rivals"],
      regions: [
        {
          region_id: "reg-1",
          owner_id: "faction-1",
          terrain: "plain",
          visibility: "visible",
          occupation: { occupier_id: "faction-2", siege_progress: 100, hold_turns: 2 },
        },
      ],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={world}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/Occupied by House Carrow/)).toBeInTheDocument();
  });

  it("shows siege progress on the selected region", () => {
    const world: CampaignWorldView = {
      ...mockWorld,
      regions: [
        {
          region_id: "reg-1",
          owner_id: "faction-1",
          terrain: "plain",
          visibility: "visible",
          siege: { besieger_id: "faction-2", progress: 35 },
        },
      ],
    };
    render(
      <StrategyLeftInspector
        selectedEntity={{ type: "region", id: "reg-1" }}
        region={mockRegion}
        world={world}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/Besieged by faction-2/)).toBeInTheDocument();
    expect(screen.getByText(/35%/)).toBeInTheDocument();
  });
});
