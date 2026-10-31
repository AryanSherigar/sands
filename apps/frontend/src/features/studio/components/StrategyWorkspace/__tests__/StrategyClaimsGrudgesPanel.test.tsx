import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import { addFaction, readStrategyFields } from "../../../lib/strategyDocument";
import { addClaim, addGrudge } from "../../../lib/strategyStart";
import { StrategyClaimsGrudgesPanel } from "../StrategyClaimsGrudgesPanel";
import type { EditStrategyFields } from "../StrategyWorkspace.types";
import type { StrategyFields } from "../../../types/strategyDocument.types";

const makeRegion = (id: string, name: string): MapRegion => ({
  id, name, terrain: "plain", outline: "M0 0", label_point: { x: 0, y: 0 }, neighbor_ids: [], source_color: null, source_ref: null,
});
const regions = [makeRegion("north", "North"), makeRegion("south", "South")];
const pair = addFaction(addFaction(readStrategyFields({}), "Ashford"), "Carrow");

const renderPanel = (fields: StrategyFields) => {
  const onEdit = vi.fn<EditStrategyFields>();
  render(<StrategyClaimsGrudgesPanel fields={fields} regions={regions} onEdit={onEdit} />);
  return { apply: () => onEdit.mock.calls.at(-1)![0](fields) };
};

describe("claims", () => {
  it("adds the chosen claim", () => {
    const { apply } = renderPanel(pair);
    fireEvent.change(screen.getByLabelText("Claiming faction"), { target: { value: "carrow" } });
    fireEvent.change(screen.getByLabelText("Claimed region"), { target: { value: "south" } });
    fireEvent.click(screen.getByRole("button", { name: "Add claim" }));
    expect(apply().claims).toEqual([{ faction_id: "carrow", region_id: "south" }]);
  });

  it("removes an existing claim", () => {
    const fields = addClaim(pair, "ashford", "north");
    const { apply } = renderPanel(fields);
    fireEvent.click(screen.getByRole("button", { name: "Remove claim of Ashford on North" }));
    expect(apply().claims).toEqual([]);
  });
});

describe("grudges", () => {
  it("disables Add grudge when holder and target are the same leader", () => {
    renderPanel(pair);
    fireEvent.change(screen.getByLabelText("Grudge target"), { target: { value: "ashford_ruler" } });
    expect(screen.getByRole("button", { name: "Add grudge" })).toBeDisabled();
  });

  it("adds a grudge between two different leaders", () => {
    const { apply } = renderPanel(pair);
    fireEvent.click(screen.getByRole("button", { name: "Add grudge" }));
    expect(apply().grudges[0]).toMatchObject({ holder_id: "ashford_ruler", target_id: "carrow_ruler", opinion: -50 });
  });

  it("edits the opinion of an existing grudge", () => {
    const fields = addGrudge(pair, "ashford_ruler", "carrow_ruler");
    const { apply } = renderPanel(fields);
    fireEvent.change(screen.getByLabelText("Opinion, Ruler of Ashford toward Ruler of Carrow"), { target: { value: "-80" } });
    expect(apply().grudges[0].opinion).toBe(-80);
  });
});
