import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DEFAULT_STRATEGY_RULES } from "../../../constants/strategyAuthoring";
import type { StrategyFields } from "../../../types/strategyDocument.types";
import { StrategyEndingsPanel } from "../StrategyEndingsPanel";

const mockFields: StrategyFields = {
  factions: [],
  leaders: [],
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

describe("StrategyEndingsPanel", () => {
  it("renders default endings toggle and checkboxes", () => {
    render(<StrategyEndingsPanel fields={mockFields} onEdit={vi.fn()} />);

    expect(screen.getByLabelText(/Use standard campaign endings/i)).toBeChecked();
    expect(screen.getByLabelText(/Hegemony victory/i)).toBeChecked();
    expect(screen.getByLabelText(/Regime fall defeat/i)).toBeChecked();
  });

  it("toggles default endings off and adds a custom ending", () => {
    const onEdit = vi.fn();
    render(<StrategyEndingsPanel fields={mockFields} onEdit={onEdit} />);

    fireEvent.click(screen.getByRole("button", { name: /Add ending condition/i }));

    expect(onEdit).toHaveBeenCalled();
    const updater = onEdit.mock.calls[0][0];
    const updated = updater(mockFields);
    expect(updated.endings).toHaveLength(1);
    expect(updated.endings[0].kind).toBe("victory");
    expect(updated.endings[0].condition.metric).toBe("region_count");
  });

  it("gives a new ending a fresh id even after a middle one was removed", () => {
    const onEdit = vi.fn();
    const existing = ["ending_1", "ending_3"].map((id) => ({
      id,
      kind: "victory" as const,
      name: id,
      condition: { kind: "comparison" as const, metric: "region_count", subject_id: null, operator: "gte", value: 4 },
      epilogue_hint: "",
    }));
    const fields = { ...mockFields, is_using_default_endings: false, endings: existing };
    render(<StrategyEndingsPanel fields={fields} onEdit={onEdit} />);

    fireEvent.click(screen.getByRole("button", { name: /Add ending condition/i }));

    const ids = onEdit.mock.calls[0][0](fields).endings.map((ending: { id: string }) => ending.id);
    expect(new Set(ids).size).toBe(3);
  });

  it("removes an authored ending", () => {
    const onEdit = vi.fn();
    const ending = {
      id: "ending_1",
      kind: "victory" as const,
      name: "Take the north",
      condition: { kind: "comparison" as const, metric: "region_count", subject_id: null, operator: "gte", value: 4 },
      epilogue_hint: "",
    };
    const fields = { ...mockFields, is_using_default_endings: false, endings: [ending] };
    render(<StrategyEndingsPanel fields={fields} onEdit={onEdit} />);

    fireEvent.click(screen.getByRole("button", { name: /remove/i }));

    expect(onEdit.mock.calls[0][0](fields).endings).toEqual([]);
  });

  it("warns that publishing needs a victory and a defeat when standard endings are off", () => {
    const fields = { ...mockFields, is_using_default_endings: false, endings: [] };
    render(<StrategyEndingsPanel fields={fields} onEdit={vi.fn()} />);

    expect(screen.getByRole("alert")).toHaveTextContent(/at least one victory and one defeat/i);
  });

  it("does not warn while standard endings are on", () => {
    render(<StrategyEndingsPanel fields={mockFields} onEdit={vi.fn()} />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
