import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyFactionCard } from "../StrategyFactionCard";
import { DEFAULT_STRATEGY_RULES } from "../../../constants/strategyAuthoring";
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
  rules: DEFAULT_STRATEGY_RULES,
  toggles: {
    is_loans_enabled: true,
    is_events_enabled: true,
    is_outrage_enabled: true,
    is_overtures_enabled: true,
    is_ai_peace_enabled: true,
    is_ai_pressure_enabled: true,
    is_ai_subsidy_enabled: true,
    is_ai_vassal_enabled: true,
    is_ai_alliance_enabled: true,
  },
  is_using_default_endings: true,
  endings: [],
  ending_toggles: {
    is_regime_fall_enabled: true,
    is_hegemony_enabled: true,
    is_negotiated_end_enabled: true,
    is_end_date_enabled: true,
    is_vassal_outcome_enabled: true,
  },
  disabled_builtin_event_ids: [],
  orders_per_turn: 6,
  event_frequency_percent: 50,
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

  it("updates AI starting stance when selected", () => {
    const onEdit = vi.fn();
    render(
      <StrategyFactionCard
        factionId="dunmere"
        fields={mockFields}
        regions={[]}
        onEdit={onEdit}
      />
    );

    const stanceSelect = screen.getByLabelText<HTMLSelectElement>(/AI starting stance/i);
    expect(stanceSelect.tagName).toBe("SELECT");
    expect(stanceSelect.innerHTML).toContain('value="turtle"');
    fireEvent.change(stanceSelect, { target: { value: "turtle" } });

    expect(onEdit).toHaveBeenCalled();
    const updater = onEdit.mock.calls[onEdit.mock.calls.length - 1][0];
    const updated = updater(mockFields);
    expect(updated.factions[0].stance_ids).toEqual(["turtle"]);
  });

  it("toggles and edits dynastic heir", () => {
    const onEdit = vi.fn();
    render(
      <StrategyFactionCard
        factionId="dunmere"
        fields={mockFields}
        regions={[]}
        onEdit={onEdit}
      />
    );

    const heirCheckbox = screen.getByLabelText(/Designate dynastic heir/i);
    fireEvent.click(heirCheckbox);

    expect(onEdit).toHaveBeenCalled();
    const updater = onEdit.mock.calls[0][0];
    const withHeir = updater(mockFields);
    expect(withHeir.leaders[0].heir?.name).toBe("Queen Mira the Younger");
  });
});
