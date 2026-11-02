import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExchangeManuscriptModal } from "../ExchangeManuscriptModal";
import { BattleAftermathModal } from "../BattleAftermathModal";
import type { ExchangeReport, NobleCaptive } from "../../StrategyWarCouncil.types";

const mockReport: ExchangeReport = {
  battle_id: "b1",
  campaign_turn: 1,
  exchange_index: 1,
  total_exchange: 1,
  own_losses: { infantry: 54, archers_siege: 0 },
  opponent_strength: { minimum: 1100, maximum: 1500 },
  outcome: null,
  observations: [
    {
      id: "r1",
      battle_id: "b1",
      observer_faction_id: "f1",
      subject_faction_id: "f2",
      mission_id: "m1",
      target: "composition",
      observed_turn: 1,
      observed_exchange: 1,
      available_from_wave: 1,
      strength: { minimum: 1000, maximum: 1400 },
      preparation_hint: "flanking",
      confidence: "medium",
    },
  ],
};

const mockCaptive: NobleCaptive = {
  nobleId: "noble-aldous",
  name: "Lord Aldous",
  title: "Duke of Westmarch",
  factionId: "ironmark",
  ransomValueGold: 500,
};

describe("ExchangeManuscriptModal", () => {
  it("renders real losses, enemy estimate and scout dispatch, and closes", () => {
    const handleAdvance = vi.fn();
    render(
      <ExchangeManuscriptModal
        report={mockReport}
        morale={78}
        isFinalWave={false}
        onAdvanceWave={handleAdvance}
      />,
    );

    expect(screen.getByText(/Wave 1 Clash Manuscript/i)).toBeInTheDocument();
    expect(screen.getByText(/78% Morale/i)).toBeInTheDocument();
    expect(screen.getByText("54 fallen")).toBeInTheDocument();
    expect(screen.getByText(/1,100–1,500/)).toBeInTheDocument();
    expect(screen.getByText(/moving to flank/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Back to the War Council/i }));
    expect(handleAdvance).toHaveBeenCalledTimes(1);
  });

  it("renders view aftermath button on the final wave", () => {
    const handleAftermath = vi.fn();
    render(
      <ExchangeManuscriptModal
        report={mockReport}
        morale={null}
        isFinalWave
        onAdvanceWave={vi.fn()}
        onViewAftermath={handleAftermath}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /View Aftermath/i }));
    expect(handleAftermath).toHaveBeenCalledTimes(1);
  });
});

describe("BattleAftermathModal", () => {
  it("renders victor banner, total losses, and calls return to realm map", () => {
    const handleReturn = vi.fn();
    render(
      <BattleAftermathModal
        outcome="attacker_victory"
        totalHostLosses={142}
        enemyStrengthRemaining={{ minimum: 480, maximum: 520 }}
        onReturnToRealmMap={handleReturn}
      />,
    );

    expect(screen.getByText(/Attacker Victory/i)).toBeInTheDocument();
    expect(screen.getByText(/142/)).toBeInTheDocument();
    expect(screen.getByText(/480–520/)).toBeInTheDocument();

    const returnBtn = screen.getByRole("button", { name: /Return to Realm Map/i });
    fireEvent.click(returnBtn);
    expect(handleReturn).toHaveBeenCalledTimes(1);
  });

  it("lists captured nobles as awaiting the sovereign's judgment with no local decisions", () => {
    render(
      <BattleAftermathModal
        outcome="defender_victory"
        totalHostLosses={80}
        enemyStrengthRemaining={null}
        nobleCaptives={[mockCaptive]}
        onReturnToRealmMap={vi.fn()}
      />,
    );

    expect(screen.getByText(/Lord Aldous/i)).toBeInTheDocument();
    expect(screen.getByText(/Duke of Westmarch/i)).toBeInTheDocument();
    expect(screen.getByText(/awaiting the sovereign's judgment/i)).toBeInTheDocument();
    expect(screen.getByText(/brought before the throne/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ransom for Gold/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Imprison in Royal Dungeon/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Pardon & Release/i })).toBeNull();
  });
});
