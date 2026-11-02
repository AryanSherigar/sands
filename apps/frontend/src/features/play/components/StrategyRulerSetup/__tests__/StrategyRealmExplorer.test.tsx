import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { StrategyRealmExplorer } from "../StrategyRealmExplorer";
import { FALLBACK_STRATEGY_MAP } from "../../StrategyPlayScreen/fallbackStrategyMap";
import type { PlayableFactionInfo } from "../StrategyRulerSetup.types";

const mockFactions: PlayableFactionInfo[] = [
  {
    id: "valenreach",
    name: "Crown of Valenreach",
    color: "#46606E",
    is_playable: true,
    provinces_count: 4,
    capital_seat: "Castle Highgard",
    government: "Feudal Monarchy",
    treasury: 340,
    manpower: 14200,
  },
  {
    id: "oakhaven",
    name: "Duchy of Oakhaven",
    color: "#5E8A5A",
    is_playable: true,
    provinces_count: 3,
    capital_seat: "Oakhaven Spire",
    government: "Duchy",
    treasury: 250,
    manpower: 8900,
  },
];

describe("StrategyRealmExplorer", () => {
  it("renders faction cards and switches active realm on click", () => {
    const onSelectFaction = vi.fn();
    render(
      <StrategyRealmExplorer
        factions={mockFactions}
        activeFactionId="valenreach"
        onSelectFaction={onSelectFaction}
        mapDoc={FALLBACK_STRATEGY_MAP}
      />
    );
    expect(screen.getByText("Crown of Valenreach")).toBeDefined();
    expect(screen.getByText("Duchy of Oakhaven")).toBeDefined();
    expect(screen.getByText("Castle Highgard")).toBeDefined();

    fireEvent.click(screen.getByText("Duchy of Oakhaven"));
    expect(onSelectFaction).toHaveBeenCalledWith("oakhaven");
  });

  it("renders realm dossier stats and crisis banner", () => {
    const onSelectFaction = vi.fn();
    render(
      <StrategyRealmExplorer
        factions={mockFactions}
        activeFactionId="valenreach"
        onSelectFaction={onSelectFaction}
        mapDoc={FALLBACK_STRATEGY_MAP}
      />
    );
    expect(screen.getByText("Castle Highgard")).toBeDefined();
    expect(screen.getByText("Feudal Monarchy")).toBeDefined();
    expect(screen.getByText(/340\s*Gold/i)).toBeDefined();
    expect(screen.getByText("14,200")).toBeDefined();
    expect(screen.getByText("Autumn Equinox Crisis")).toBeDefined();
  });

  it("renders map capital pins and clicking pin switches active realm", () => {
    const onSelectFaction = vi.fn();
    render(
      <StrategyRealmExplorer
        factions={mockFactions}
        activeFactionId="valenreach"
        onSelectFaction={onSelectFaction}
        mapDoc={FALLBACK_STRATEGY_MAP}
        regionOwners={{ "reg-dunmere": "valenreach", "reg-greenford": "oakhaven" }}
      />
    );
    const oakhavenPin = screen.getByTestId("map-pin-oakhaven");
    expect(oakhavenPin).toBeDefined();
    fireEvent.click(oakhavenPin);
    expect(onSelectFaction).toHaveBeenCalledWith("oakhaven");
  });

  it("handles clicking legend pill button to select faction", () => {
    const onSelectFaction = vi.fn();
    render(
      <StrategyRealmExplorer
        factions={mockFactions}
        activeFactionId="valenreach"
        onSelectFaction={onSelectFaction}
        mapDoc={FALLBACK_STRATEGY_MAP}
      />
    );
    const oakhavenLegend = screen.getByTestId("map-legend-oakhaven");
    fireEvent.click(oakhavenLegend);
    expect(onSelectFaction).toHaveBeenCalledWith("oakhaven");
  });

  it("shows a notice instead of a made-up map when the scenario has none", () => {
    render(
      <StrategyRealmExplorer
        factions={mockFactions}
        activeFactionId="valenreach"
        onSelectFaction={vi.fn()}
      />
    );
    expect(screen.getByText("This realm has no map to show yet.")).toBeDefined();
    expect(screen.queryByTestId("map-pin-valenreach")).toBeNull();
  });

  it("names the scenario's start year instead of a fixed one", () => {
    render(
      <StrategyRealmExplorer
        factions={mockFactions}
        activeFactionId="valenreach"
        onSelectFaction={vi.fn()}
        startYear={1187}
      />
    );
    expect(screen.getByText(/campaign of 1187/)).toBeDefined();
    expect(screen.queryByText(/1042/)).toBeNull();
  });
});
