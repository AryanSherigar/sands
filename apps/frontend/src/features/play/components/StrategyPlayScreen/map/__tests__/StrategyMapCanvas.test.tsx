import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyMapCanvas } from "../StrategyMapCanvas";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import type { CampaignWorldView } from "../../../../types/simulation.types";

const mockDocument: MapDocument = {
  schema_version: 1,
  source: "manual",
  width: 1600,
  height: 900,
  image_url: "/uploads/map.png",
  regions: [
    {
      id: "reg-1",
      name: "Dunmere Vale",
      terrain: "plain",
      outline: "M0 0 L100 0 L100 100 Z",
      label_point: { x: 50, y: 50 },
      neighbor_ids: ["reg-2"],
      source_color: null,
      source_ref: null,
    },
  ],
  roads: [],
};

const mockWorld: CampaignWorldView = {
  world_version: 1,
  turn: 1,
  wave: 0,
  status: "planning",
  battles: [],
  clock: { turn: 1, start_year: 1200, start_month: 3 },
  my_faction: {
    id: "fac-player",
    treasury: 1000,
    manpower: 5000,
    stability: 80,
    war_exhaustion: 0,
    reputation: 50,
    tax_rate: "normal",
    loans: [],
  },
  ruler: { name: "Lord Vance" },
  regions: [
    {
      region_id: "reg-1",
      owner_id: "fac-player",
      terrain: "plain",
      visibility: "visible",
      detail: {
        id: "reg-1",
        owner_id: "fac-player",
        population: 20000,
        wealth: 50,
        manpower: 100,
        unrest: 75,
        garrison: 500,
        faith_id: "old-gods",
        improvements: [],
        claimant_ids: [],
        conversion_turns_remaining: 0,
      },
    },
  ],
  armies: [
    {
      army_id: "army-1",
      owner_id: "fac-enemy",
      location_id: "reg-1",
      commander_name: "Iron Vanguard",
      troops: { infantry: 1200, cavalry: 300 },
    },
  ],
  rivals: [],
  queued_orders: [],
  orders_remaining: 3,
};

describe("StrategyMapCanvas", () => {
  it("renders background image and region pin", () => {
    const onSelect = vi.fn();
    render(
      <StrategyMapCanvas
        document={mockDocument}
        world={undefined}
        onSelectEntity={onSelect}
      />,
    );
    expect(screen.getByAltText("Grand Strategy Map")).toBeInTheDocument();
    expect(screen.getByText("Dunmere Vale")).toBeInTheDocument();
  });

  it("triggers selection when region is clicked", () => {
    const onSelect = vi.fn();
    render(
      <StrategyMapCanvas
        document={mockDocument}
        world={undefined}
        onSelectEntity={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("Dunmere Vale"));
    expect(onSelect).toHaveBeenCalledWith({ type: "region", id: "reg-1" });
  });

  it("renders army banner and triggers army selection when clicked", () => {
    const onSelect = vi.fn();
    render(
      <StrategyMapCanvas
        document={mockDocument}
        world={mockWorld}
        onSelectEntity={onSelect}
      />,
    );
    expect(screen.getByText("Iron Vanguard")).toBeInTheDocument();
    expect(screen.getByText("1,500")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Iron Vanguard"));
    expect(onSelect).toHaveBeenCalledWith({ type: "army", id: "army-1" });
  });

  it("renders crisis alert pin when unrest exceeds threshold", () => {
    const onSelect = vi.fn();
    render(
      <StrategyMapCanvas
        document={mockDocument}
        world={mockWorld}
        onSelectEntity={onSelect}
      />,
    );
    expect(screen.getByText("Unrest 75%")).toBeInTheDocument();
  });

  it("deselects entity when background map is clicked", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <StrategyMapCanvas
        document={mockDocument}
        world={mockWorld}
        onSelectEntity={onSelect}
      />,
    );
    const background = container.firstElementChild as HTMLElement;
    fireEvent.click(background);
    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
