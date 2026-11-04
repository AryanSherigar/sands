import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { StrategyProclamationDialog } from "../StrategyProclamationDialog";
import type { ProclamationMinisterView } from "../../../../api/proclamation.api";

describe("StrategyProclamationDialog", () => {
  const sampleMinisters: ProclamationMinisterView[] = [
    {
      estate: "nobility",
      title: "Lord Chancellor Morvath",
      stance: "oppose",
      primary_grievance: "Feudal charters",
    },
    {
      estate: "military",
      title: "High Marshal Vane",
      stance: "support",
      primary_grievance: "Garrison readiness",
    },
    {
      estate: "burghers",
      title: "Lord Treasurer Hest",
      stance: "cautious",
      primary_grievance: "Coin reserves",
    },
    {
      estate: "clergy",
      title: "Arch-Prelate Tomas",
      stance: "oppose",
      primary_grievance: "Canonical tithes",
    },
  ];

  it("renders all four ministers with their estate badges and initial stances", () => {
    render(
      <StrategyProclamationDialog
        isOpen={true}
        ministers={sampleMinisters}
        legalSummary="Levy 200 silver from merchants."
        onPronounce={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText("Lord Chancellor Morvath")).toBeInTheDocument();
    expect(screen.getByText("High Marshal Vane")).toBeInTheDocument();
    expect(screen.getByText("Lord Treasurer Hest")).toBeInTheDocument();
    expect(screen.getByText("Arch-Prelate Tomas")).toBeInTheDocument();
  });

  it("triggers pronouncement callbacks for fiat and compromise", async () => {
    const onPronounce = vi.fn();
    const user = userEvent.setup();
    render(
      <StrategyProclamationDialog
        isOpen={true}
        ministers={sampleMinisters}
        legalSummary="Levy 200 silver from merchants."
        onPronounce={onPronounce}
        onClose={vi.fn()}
      />
    );

    const fiatBtn = screen.getByRole("button", { name: /rule by fiat/i });
    const compBtn = screen.getByRole("button", { name: /adopt compromise/i });

    await user.click(fiatBtn);
    expect(onPronounce).toHaveBeenCalledWith("fiat");

    await user.click(compBtn);
    expect(onPronounce).toHaveBeenCalledWith("compromise");
  });

  it("shows each speaker in a separate block and the streaming indicator", () => {
    render(
      <StrategyProclamationDialog
        isOpen={true}
        ministers={sampleMinisters}
        legalSummary="Levy 200 silver from merchants."
        transcript={[
          { speaker: "CHANCELLOR", text: "The barons object." },
          { speaker: "MARSHAL", text: "The border burns." },
          { speaker: "SOVEREIGN", text: "The Crown decides." },
        ]}
        isStreaming={true}
        onPronounce={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText("“The barons object.”")).toBeInTheDocument();
    expect(screen.getByText("“The border burns.”")).toBeInTheDocument();
    expect(screen.getByText("“The Crown decides.”")).toBeInTheDocument();
    expect(screen.getByText("The Sovereign")).toBeInTheDocument();
    expect(screen.getByText(/the council continues its debate/i)).toBeInTheDocument();
  });

  it("shows the silent-chamber state and disables decisions while enacting", () => {
    render(
      <StrategyProclamationDialog
        isOpen={true}
        ministers={sampleMinisters}
        legalSummary="Levy 200 silver from merchants."
        isEnacting={true}
        onPronounce={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText(/solemn silence/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rule by fiat/i })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/great seal/i);
  });
});
