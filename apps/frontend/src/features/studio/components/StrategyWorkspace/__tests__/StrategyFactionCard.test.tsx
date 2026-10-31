import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyFactionCard } from "../StrategyFactionCard";
import type { StrategyFields } from "../../../types/strategyDocument.types";

const mockFields: StrategyFields = {
  factions: [
    {
      id: "dunmere",
      name: "Dunmere",
      color: "#ff0000",
      capital_region_id: "reg-1",
      leader_id: "mira",
      treasury: 500,
      manpower: 10000,
      stability: 50,
      is_playable: true,
    },
  ],
  leaders: [
    {
      id: "mira",
      name: "Queen Mira",
      faction_id: "dunmere",
      trait_ids: ["cautious", "proud"],
      ambition_ids: ["wealth"],
      history: "A cunning monarch.",
      age: 32,
      avatar_url: null,
    },
  ],
  ambitions: [],
  regions: [],
  armies: [],
  commanders: [],
  relations: [],
  claims: [],
  grudges: [],
  timing: { start_year: 1000, start_month: 3, end_year: 1004 },
};

describe("StrategyFactionCard Avatar Integration", () => {
  it("renders faction details and Leader Avatar section", () => {
    render(
      <StrategyFactionCard
        factionId="dunmere"
        fields={mockFields}
        regions={[]}
        onEdit={vi.fn()}
      />
    );

    expect(screen.getByText("Leader Avatar")).toBeInTheDocument();
    expect(screen.getByText("No animated avatar")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate Avatar/i })).toBeInTheDocument();
  });

  it("opens LeaderAvatarCreatorModal when clicking Generate Avatar", () => {
    render(
      <StrategyFactionCard
        factionId="dunmere"
        fields={mockFields}
        regions={[]}
        onEdit={vi.fn()}
      />
    );

    const generateBtn = screen.getByRole("button", { name: /Generate Avatar/i });
    fireEvent.click(generateBtn);

    expect(screen.getByRole("dialog", { name: /Generate Animated Leader Avatar/i })).toBeInTheDocument();
    expect(screen.getByText(/Animated Avatar Studio/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Stern elven queen/i)).toBeInTheDocument();
  });

  it("shows the portrait thumbnail when the leader has a portrait but no avatar", () => {
    const withPortrait: StrategyFields = {
      ...mockFields,
      leaders: [{ ...mockFields.leaders[0], portrait_url: "https://cdn.test/p.webp" }],
    };
    render(
      <StrategyFactionCard
        factionId="dunmere"
        fields={withPortrait}
        regions={[]}
        onEdit={vi.fn()}
      />
    );

    expect(screen.getByRole("img", { name: /Queen Mira portrait/i })).toHaveAttribute(
      "src",
      "https://cdn.test/p.webp",
    );
  });
});
