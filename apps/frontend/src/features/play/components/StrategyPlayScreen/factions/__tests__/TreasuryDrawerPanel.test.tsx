import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TreasuryDrawerPanel } from "../TreasuryDrawerPanel";
import type { CampaignWorldView } from "../../../../types/simulation.types";

function makeWorld(overrides: Partial<CampaignWorldView> = {}): CampaignWorldView {
  return {
    turn: 1,
    orders_remaining: 3,
    my_faction: {
      id: "f-1",
      leader_id: null,
      treasury: 400,
      manpower: 5000,
      stability: 60,
      war_exhaustion: 10,
      reputation: 0,
      tax_rate: "normal",
      loans: [],
    },
    ruler: { name: "King Aldric" },
    regions: [],
    armies: [],
    rivals: [],
    pacts: [],
    clock: { turn: 1, start_year: 1042, start_month: 3 },
    ...overrides,
  } as CampaignWorldView;
}

describe("TreasuryDrawerPanel", () => {
  it("renders all three section headings", () => {
    render(<TreasuryDrawerPanel world={makeWorld()} onSubmitOrder={vi.fn()} />);
    expect(screen.getByText(/Tax Rate/i)).toBeInTheDocument();
    expect(screen.getByText(/Sovereign Credit/i)).toBeInTheDocument();
    expect(screen.getByText(/Sovereign Default/i)).toBeInTheDocument();
  });

  it("highlights the current tax rate button", () => {
    render(<TreasuryDrawerPanel world={makeWorld()} onSubmitOrder={vi.fn()} />);
    const normalBtn = screen.getByRole("button", { name: /Normal/i });
    expect(normalBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onSubmitOrder with set_tax_rate when a different rate is clicked", () => {
    const onSubmitOrder = vi.fn();
    render(<TreasuryDrawerPanel world={makeWorld()} onSubmitOrder={onSubmitOrder} />);
    fireEvent.click(screen.getByRole("button", { name: /High/i }));
    expect(onSubmitOrder).toHaveBeenCalledWith({
      kind: "set_tax_rate",
      faction_id: "f-1",
      tax_rate: "high",
    });
  });

  it("does not call onSubmitOrder when the already-active rate is clicked", () => {
    const onSubmitOrder = vi.fn();
    render(<TreasuryDrawerPanel world={makeWorld()} onSubmitOrder={onSubmitOrder} />);
    fireEvent.click(screen.getByRole("button", { name: /Normal/i }));
    expect(onSubmitOrder).not.toHaveBeenCalled();
  });

  it("calls onSubmitOrder with take_loan when Contract Loan is clicked with an amount", () => {
    const onSubmitOrder = vi.fn();
    render(<TreasuryDrawerPanel world={makeWorld()} onSubmitOrder={onSubmitOrder} />);
    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "200" } });
    fireEvent.click(screen.getByRole("button", { name: /Contract Loan/i }));
    expect(onSubmitOrder).toHaveBeenCalledWith({
      kind: "take_loan",
      faction_id: "f-1",
      amount: 200,
    });
  });

  it("disables Contract Loan button when amount is 0", () => {
    render(<TreasuryDrawerPanel world={makeWorld()} onSubmitOrder={vi.fn()} />);
    const btn = screen.getByRole("button", { name: /Contract Loan/i });
    expect(btn).toBeDisabled();
  });

  it("calls onSubmitOrder with declare_default when Declare Default is clicked", () => {
    const onSubmitOrder = vi.fn();
    render(<TreasuryDrawerPanel world={makeWorld()} onSubmitOrder={onSubmitOrder} />);
    fireEvent.click(screen.getByRole("button", { name: /Declare Default/i }));
    expect(onSubmitOrder).toHaveBeenCalledWith({
      kind: "declare_default",
      faction_id: "f-1",
    });
  });

  it("shows outstanding loan principal when loans exist", () => {
    const world = makeWorld({
      my_faction: {
        ...makeWorld().my_faction,
        loans: [{ principal: 300, interest_percent: 4, turns_remaining: 10 }],
      } as CampaignWorldView["my_faction"],
    });
    render(<TreasuryDrawerPanel world={world} onSubmitOrder={vi.fn()} />);
    expect(screen.getByText(/300/)).toBeInTheDocument();
  });

  it("renders income estimate when region details are present", () => {
    const world = makeWorld({
      regions: [
        {
          region_id: "r-1",
          owner_id: "f-1",
          terrain: "plains",
          visibility: "visible",
          detail: {
            id: "r-1",
            owner_id: "f-1",
            population: 1000,
            wealth: 100,
            manpower: 50,
            unrest: 10,
            garrison: 20,
            faith_id: null,
            improvements: [],
            claimant_ids: [],
            conversion_turns_remaining: 0,
          },
        },
      ],
    });
    render(<TreasuryDrawerPanel world={world} onSubmitOrder={vi.fn()} />);
    // wealth 100 * normal(0.8) * (100 - 10) / 100 = 72
    expect(screen.getByText(/~72g income this turn at normal tax/i)).toBeInTheDocument();
  });
});
