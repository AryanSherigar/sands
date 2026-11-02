import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { BattleView } from "../../StrategyWarCouncil.types";
import { CodexTacticsDrawer } from "../CodexTacticsDrawer";

const BATTLE: BattleView = {
  id: "b1",
  region_id: "r1",
  status: "awaiting_commands",
  outcome: null,
  current_turn: 1,
  exchanges_used: 0,
  total_exchanges: 0,
  is_big: true,
  control_mode: "player",
  terrain: "hills",
  weather: "rain",
  command_cost: 1,
  frontage: 2400,
  own_contingent: {
    faction_id: "f1",
    army_ids: [],
    troops: { infantry: 100 },
    morale: 90,
    fatigue: 0,
    plan: {
      formation: "defensive",
      tactic: "press",
      withdrawal_policy: "balanced",
      reserve_policy: "reinforce_on_pressure",
    },
    supply: "strained",
    status: "fighting",
  },
  opponents: [],
  legal_commands: [],
};

describe("CodexTacticsDrawer", () => {
  it("shows this battle's real conditions and no invented percentages", () => {
    const handleClose = vi.fn();
    render(<CodexTacticsDrawer isOpen battle={BATTLE} onClose={handleClose} />);

    expect(screen.getByText("Codex of War & Terrain")).toBeInTheDocument();
    expect(screen.getByText("Hills")).toBeInTheDocument();
    expect(screen.getByText("Rain")).toBeInTheDocument();
    expect(screen.getByText("Supply strained")).toBeInTheDocument();
    expect(screen.getByText("2,400 troops can fight abreast")).toBeInTheDocument();
    expect(screen.getByText("Feed reserves in when the line is under pressure.")).toBeInTheDocument();
    expect(screen.queryByText(/%/)).toBeNull();
    expect(screen.queryByText("Tactical Balance Formula")).toBeNull();

    fireEvent.click(screen.getByText("Done Reading"));
    expect(handleClose).toHaveBeenCalled();
  });

  it("renders nothing when closed", () => {
    const { container } = render(<CodexTacticsDrawer isOpen={false} battle={BATTLE} onClose={vi.fn()} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("closes on Escape and moves focus into the panel", () => {
    const handleClose = vi.fn();
    render(<CodexTacticsDrawer isOpen battle={BATTLE} onClose={handleClose} />);

    expect(screen.getByRole("dialog").contains(document.activeElement)).toBe(true);
    fireEvent.keyDown(document, { key: "Escape" });

    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
