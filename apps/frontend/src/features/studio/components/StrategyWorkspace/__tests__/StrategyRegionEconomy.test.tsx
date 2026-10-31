import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import { addFaction, readStrategyFields, setRegionOwner } from "../../../lib/strategyDocument";
import { StrategyRegionEconomy } from "../StrategyRegionEconomy";
import type { EditStrategyFields } from "../StrategyWorkspace.types";
import type { StrategyFields } from "../../../types/strategyDocument.types";

const makeRegion = (id: string, name: string): MapRegion => ({
  id,
  name,
  terrain: "plain",
  outline: "M0 0",
  label_point: { x: 0, y: 0 },
  neighbor_ids: [],
  source_color: null,
  source_ref: null,
});

const regions = [makeRegion("north", "North"), makeRegion("south", "South")];
const fields: StrategyFields = setRegionOwner(addFaction(readStrategyFields({}), "Ashford"), "north", "ashford");

const renderPanel = () => {
  const onEdit = vi.fn<EditStrategyFields>();
  render(<StrategyRegionEconomy fields={fields} regions={regions} onEdit={onEdit} />);
  return onEdit;
};

const commit = (onEdit: ReturnType<typeof renderPanel>, label: string, raw: string): StrategyFields => {
  const input = screen.getByLabelText(label);
  fireEvent.change(input, { target: { value: raw } });
  fireEvent.blur(input);
  return onEdit.mock.calls.at(-1)![0](fields);
};

describe("StrategyRegionEconomy", () => {
  it("shows seeded defaults for an owned region", () => {
    renderPanel();
    expect(screen.getByLabelText("Wealth of North")).toHaveValue("50");
  });

  it("commits an edited wealth", () => {
    const onEdit = renderPanel();
    expect(commit(onEdit, "Wealth of North", "40").regions[0].wealth).toBe(40);
  });

  it("clamps unrest to 100", () => {
    const onEdit = renderPanel();
    expect(commit(onEdit, "Unrest of North", "300").regions[0].unrest).toBe(100);
  });

  it("renders no inputs for an unowned region", () => {
    renderPanel();
    expect(screen.getByText(/South/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Wealth of South")).not.toBeInTheDocument();
    expect(screen.getByText(/no economy/i)).toBeInTheDocument();
  });
});
