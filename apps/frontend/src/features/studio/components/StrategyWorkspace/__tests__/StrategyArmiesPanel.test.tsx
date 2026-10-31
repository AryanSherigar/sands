import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import { addFaction, readStrategyFields, setRegionOwner, updateFaction } from "../../../lib/strategyDocument";
import { removeArmy } from "../../../lib/strategyStart";
import { StrategyArmiesPanel } from "../StrategyArmiesPanel";
import type { EditStrategyFields } from "../StrategyWorkspace.types";
import type { StrategyFields } from "../../../types/strategyDocument.types";

const makeRegion = (id: string, name: string): MapRegion => ({
  id, name, terrain: "plain", outline: "M0 0", label_point: { x: 0, y: 0 }, neighbor_ids: [], source_color: null, source_ref: null,
});
const regions = [makeRegion("north", "North"), makeRegion("south", "South")];

const withoutArmies = (input: StrategyFields): StrategyFields =>
  input.armies.reduce((current, army) => removeArmy(current, army.id), input);

const base = (): StrategyFields => {
  let fields = addFaction(addFaction(readStrategyFields({}), "Ashford"), "Carrow");
  fields = setRegionOwner(setRegionOwner(fields, "north", "ashford"), "south", "carrow");
  return withoutArmies(updateFaction(fields, "ashford", { capital_region_id: "north" }));
};

const renderPanel = (fields: StrategyFields) => {
  const onEdit = vi.fn<EditStrategyFields>();
  render(<StrategyArmiesPanel fields={fields} regions={regions} onEdit={onEdit} />);
  return { onEdit, apply: () => onEdit.mock.calls.at(-1)![0](fields) };
};

describe("StrategyArmiesPanel", () => {
  it("adds an army at the capital with default troops and morale 70", () => {
    const { apply } = renderPanel(base());
    fireEvent.click(screen.getByRole("button", { name: "Add army for Ashford" }));
    expect(apply().armies[0]).toMatchObject({ owner_id: "ashford", location_id: "north", morale: 70, troops: { infantry: 250 } });
  });

  it("commits an infantry count", () => {
    const fields = base();
    const withArmy = { ...fields, armies: [{ id: "a1", owner_id: "ashford", location_id: "north", troops: { infantry: 250 }, commander_id: null, morale: 70 }] };
    const { onEdit } = renderPanel(withArmy);
    const input = screen.getByLabelText("Infantry (a1)");
    fireEvent.change(input, { target: { value: "500" } });
    fireEvent.blur(input);
    expect(onEdit.mock.calls.at(-1)![0](withArmy).armies[0].troops.infantry).toBe(500);
  });

  it("removes an army", () => {
    const withArmy = { ...base(), armies: [{ id: "a1", owner_id: "ashford", location_id: "north", troops: { infantry: 250 }, commander_id: null, morale: 70 }] };
    const { onEdit } = renderPanel(withArmy);
    fireEvent.click(screen.getByRole("button", { name: "Remove a1" }));
    expect(onEdit.mock.calls.at(-1)![0](withArmy).armies).toEqual([]);
  });

  it("disables Add army for a faction that owns no region", () => {
    const fields = addFaction(readStrategyFields({}), "Lonely");
    renderPanel(fields);
    expect(screen.getByRole("button", { name: "Add army for Lonely" })).toBeDisabled();
  });

  it("warns when an army stands in foreign territory", () => {
    const withArmy = { ...base(), armies: [{ id: "a1", owner_id: "ashford", location_id: "south", troops: { infantry: 250 }, commander_id: null, morale: 70 }] };
    renderPanel(withArmy);
    expect(screen.getByText("In foreign territory")).toBeInTheDocument();
  });

  it("creates a commander when a name is committed and links it to the army", () => {
    const withArmy = { ...base(), armies: [{ id: "a1", owner_id: "ashford", location_id: "north", troops: { infantry: 250 }, commander_id: null, morale: 70 }] };
    const { onEdit } = renderPanel(withArmy);
    const input = screen.getByLabelText("Commander (a1)");
    fireEvent.change(input, { target: { value: "Ser Aldric" } });
    fireEvent.blur(input);
    const next = onEdit.mock.calls.at(-1)![0](withArmy);
    expect(next.commanders).toEqual([
      { id: "a1_commander", name: "Ser Aldric", faction_id: "ashford", trait_ids: [], is_important: false },
    ]);
    expect(next.armies[0].commander_id).toBe("a1_commander");
  });

  it("sets two distinct traits and drops the commander when the name is cleared", () => {
    const commander = { id: "c1", name: "Ser Aldric", faction_id: "ashford", trait_ids: [], is_important: false };
    const withArmy = { ...base(), commanders: [commander], armies: [{ id: "a1", owner_id: "ashford", location_id: "north", troops: { infantry: 250 }, commander_id: "c1", morale: 70 }] };
    const { onEdit } = renderPanel(withArmy);
    fireEvent.change(screen.getByLabelText("Commander trait 1 (a1)"), { target: { value: "cunning" } });
    expect(onEdit.mock.calls.at(-1)![0](withArmy).commanders[0].trait_ids).toEqual(["cunning"]);
    const input = screen.getByLabelText("Commander (a1)");
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.blur(input);
    const cleared = onEdit.mock.calls.at(-1)![0](withArmy);
    expect(cleared.commanders).toEqual([]);
    expect(cleared.armies[0].commander_id).toBeNull();
  });

  it("removes the commander together with the army", () => {
    const commander = { id: "c1", name: "Ser Aldric", faction_id: "ashford", trait_ids: [], is_important: false };
    const withArmy = { ...base(), commanders: [commander], armies: [{ id: "a1", owner_id: "ashford", location_id: "north", troops: { infantry: 250 }, commander_id: "c1", morale: 70 }] };
    const { onEdit } = renderPanel(withArmy);
    fireEvent.click(screen.getByRole("button", { name: "Remove a1" }));
    expect(onEdit.mock.calls.at(-1)![0](withArmy).commanders).toEqual([]);
  });
});
