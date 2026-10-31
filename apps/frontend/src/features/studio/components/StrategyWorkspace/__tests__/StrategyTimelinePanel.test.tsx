import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { readStrategyFields } from "../../../lib/strategyDocument";
import { StrategyTimelinePanel } from "../StrategyTimelinePanel";
import type { EditStrategyFields } from "../StrategyWorkspace.types";

const fields = readStrategyFields({});

const renderPanel = () => {
  const onEdit = vi.fn<EditStrategyFields>();
  render(<StrategyTimelinePanel fields={fields} onEdit={onEdit} />);
  return { apply: () => onEdit.mock.calls.at(-1)![0](fields) };
};

describe("StrategyTimelinePanel", () => {
  it("shows the Studio default end year and the turn estimate", () => {
    renderPanel();
    expect(screen.getByLabelText("End year")).toHaveValue("1004");
    expect(screen.getByText("About 29 turns")).toBeInTheDocument();
  });

  it("keeps the end year after the start year", () => {
    const { apply } = renderPanel();
    const input = screen.getByLabelText("End year");
    fireEvent.change(input, { target: { value: "1000" } });
    fireEvent.blur(input);
    expect(apply().timing.end_year).toBe(1001);
  });

  it("changes the start month", () => {
    const { apply } = renderPanel();
    fireEvent.change(screen.getByLabelText("Start month"), { target: { value: "5" } });
    expect(apply().timing.start_month).toBe(5);
  });
});
