import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { KnownFactionsLedger } from "../KnownFactionsLedger";
import type { RivalView } from "../../../../types/simulation.types";
import type { StrategyDiplomacyProps } from "../../../../types/scene.types";
import { makeCampaignWorld } from "../../../../test-utils/eventFixtures";


const RANGE = { low: 0, high: 50 };
const RIVALS: RivalView[] = [
  { faction_id: "house_ashford", name: "House Ashford", leader_name: "Mira", relation: "peace", treasury_range: RANGE, manpower_range: RANGE },
  { faction_id: "house_dunwick", name: "House Dunwick", leader_name: "Harl", relation: "war", treasury_range: RANGE, manpower_range: RANGE },
];

const PLAYER_FACTION_ID = "house_carrow";
const WORLD = makeCampaignWorld({
  my_faction: { ...makeCampaignWorld().my_faction, id: PLAYER_FACTION_ID },
});

function diplomacy(overrides: Partial<StrategyDiplomacyProps> = {}): StrategyDiplomacyProps {
  return { pacts: [], isProposalAvailable: true, onProposeTerms: vi.fn(), ...overrides };
}

describe("KnownFactionsLedger diplomacy", () => {
  it("offers terms to a faction at peace and reports the choice", () => {
    const props = diplomacy();
    render(<KnownFactionsLedger rivals={RIVALS} diplomacy={props} />);
    const buttons = screen.getAllByRole("button", { name: "Propose terms" });
    expect(buttons).toHaveLength(1);
    fireEvent.click(buttons[0]);
    expect(props.onProposeTerms).toHaveBeenCalledWith("house_ashford");
  });

  it("hides the action while planning is closed", () => {
    render(
      <KnownFactionsLedger rivals={RIVALS} diplomacy={diplomacy({ isProposalAvailable: false })} />,
    );
    expect(screen.queryByRole("button", { name: "Propose terms" })).not.toBeInTheDocument();
  });

  it("shows an active pact instead of offering another", () => {
    const pacts = [
      { commitment_id: "commitment_1", faction_a: "house_ashford", faction_b: "house_carrow", start_turn: 4, end_turn: 12 },
    ];
    render(<KnownFactionsLedger rivals={RIVALS} world={WORLD} diplomacy={diplomacy({ pacts })} />);
    expect(screen.getByText("Non-aggression pact until turn 12")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Propose terms" })).not.toBeInTheDocument();
  });

  it("ignores pacts between two other houses", () => {
    const pacts = [
      { commitment_id: "commitment_10", faction_a: "house_ashford", faction_b: "house_ellory", start_turn: 2, end_turn: 14 },
    ];
    render(<KnownFactionsLedger rivals={RIVALS} world={WORLD} diplomacy={diplomacy({ pacts })} />);
    expect(screen.queryByText(/Non-aggression pact/)).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Propose terms" })).toHaveLength(1);
  });

  it("works without diplomacy props, as in the preview", () => {
    render(<KnownFactionsLedger rivals={RIVALS} />);
    expect(screen.getByText("House Ashford")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Propose terms" })).not.toBeInTheDocument();
  });
});
