import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { readStrategyFields } from "../../../lib/strategyDocument";
import { StrategyRulesPanel } from "../StrategyRulesPanel";
import type { EditStrategyFields } from "../StrategyWorkspace.types";

const fields = readStrategyFields({});

const renderPanel = () => {
  const onEdit = vi.fn<EditStrategyFields>();
  render(<StrategyRulesPanel fields={fields} onEdit={onEdit} />);
  return { apply: () => onEdit.mock.calls.at(-1)![0](fields) };
};

describe("StrategyRulesPanel", () => {
  it("shows the engine defaults when the document sets nothing", () => {
    renderPanel();
    expect(screen.getByLabelText("Trade deal value per turn")).toHaveValue("4");
    expect(screen.getByLabelText("Length of an offered oath (turns)")).toHaveValue("12");
    expect(screen.getByRole("checkbox", { name: /spymasters/i })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: /revolts can be talked down/i })).not.toBeChecked();
  });

  it("turns spymasters on", () => {
    const { apply } = renderPanel();
    fireEvent.click(screen.getByRole("checkbox", { name: /spymasters/i }));
    expect(apply().rules.agents_enabled).toBe(true);
  });

  it("keeps clause weights at or below the 200 percent ceiling", () => {
    const { apply } = renderPanel();
    const input = screen.getByLabelText("Gate clause weight (%)");
    fireEvent.change(input, { target: { value: "999" } });
    fireEvent.blur(input);
    expect(apply().rules.conditional_gate_percent).toBe(200);
  });

  it("never lets an oath last less than one turn", () => {
    const { apply } = renderPanel();
    const input = screen.getByLabelText("Length of an offered oath (turns)");
    fireEvent.change(input, { target: { value: "0" } });
    fireEvent.blur(input);
    expect(apply().rules.oath_offer_duration_turns).toBe(1);
  });

  it("changes order points per turn", () => {
    const { apply } = renderPanel();
    const input = screen.getByLabelText("Order points per turn");
    fireEvent.change(input, { target: { value: "10" } });
    fireEvent.blur(input);
    expect(apply().orders_per_turn).toBe(10);
  });

  it("toggles a disaster off to disable it", () => {
    const { apply } = renderPanel();
    const plagueCheckbox = screen.getByRole("checkbox", { name: /Plague & pestilence/i });
    expect(plagueCheckbox).toBeChecked();
    fireEvent.click(plagueCheckbox);
    expect(apply().disabled_builtin_event_ids).toContain("plague");
  });

  it("toggles a subsystem switch", () => {
    const { apply } = renderPanel();
    const loansCheckbox = screen.getByRole("checkbox", { name: /Moneylending & debt defaults/i });
    expect(loansCheckbox).toBeChecked();
    fireEvent.click(loansCheckbox);
    expect(apply().toggles.is_loans_enabled).toBe(false);
  });
});
