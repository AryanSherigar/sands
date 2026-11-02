import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EnemyCrestIntel } from "../EnemyCrestIntel";
import type { OpponentView } from "../../StrategyWarCouncil.types";

const mockOpponent: OpponentView = {
  faction_id: "ironmark",
  strength: { minimum: 800, maximum: 1200 },
  reports: [
    {
      id: "r1",
      battle_id: "b1",
      observer_faction_id: "f1",
      subject_faction_id: "ironmark",
      mission_id: "m1",
      target: "reserves",
      observed_turn: 2,
      observed_exchange: 1,
      available_from_wave: 1,
      strength: { minimum: 900, maximum: 1100 },
      reserves: { minimum: 100, maximum: 200 },
      preparation_hint: "holding",
      confidence: "high",
    },
  ],
};

describe("EnemyCrestIntel", () => {
  it("labels wing cards as illustrative and lists real scouting reports", () => {
    render(
      <EnemyCrestIntel
        scoutedTurnText="Latest scouting report from turn 2"
        opponent={mockOpponent}
        canScout
        onOrderScout={vi.fn()}
      />,
    );

    expect(screen.getByText("Latest scouting report from turn 2")).toBeInTheDocument();
    expect(screen.getByText(/Enemy Left Wing \(Illustrative\)/)).toBeInTheDocument();
    expect(screen.getByText(/reserves 100–200/)).toBeInTheDocument();
    expect(screen.getByText(/high confidence/)).toBeInTheDocument();
  });

  it("sends the chosen scouting target", () => {
    const handleScout = vi.fn();
    render(
      <EnemyCrestIntel scoutedTurnText="" opponent={mockOpponent} canScout onOrderScout={handleScout} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Scout preparation" }));
    expect(handleScout).toHaveBeenCalledWith("preparation");
  });

  it("disables scouting when the backend does not allow it", () => {
    render(
      <EnemyCrestIntel scoutedTurnText="" opponent={mockOpponent} canScout={false} onOrderScout={vi.fn()} />,
    );

    expect(screen.getByRole("button", { name: "Scout composition" })).toBeDisabled();
  });
});
