import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyFactionCard } from "../StrategyFactionCard";
import { readStrategyFields } from "../../../lib/strategyDocument";
import type { EditStrategyFields } from "../StrategyWorkspace.types";
import type { StrategyFields } from "../../../types/strategyDocument.types";

const fields: StrategyFields = {
  ...readStrategyFields({}),
  factions: [
    { id: "dunmere", name: "Dunmere", color: "#ff0000", capital_region_id: null, leader_id: "mira", treasury: 100, manpower: 400, stability: 60, is_playable: true },
  ],
  leaders: [
    { id: "mira", name: "Mira", faction_id: "dunmere", trait_ids: ["cautious", "proud"], ambition_ids: [], history: "", age: 32 },
  ],
};

const renderCard = () => {
  const onEdit = vi.fn<EditStrategyFields>();
  render(<StrategyFactionCard factionId="dunmere" fields={fields} regions={[]} onEdit={onEdit} />);
  const commit = (label: string, raw: string): StrategyFields => {
    const input = screen.getByLabelText(label);
    fireEvent.change(input, { target: { value: raw } });
    fireEvent.blur(input);
    return onEdit.mock.calls.at(-1)![0](fields);
  };
  return { commit };
};

describe("faction starting resources", () => {
  it("commits treasury as a whole number on blur", () => {
    expect(renderCard().commit("Treasury", "250").factions[0].treasury).toBe(250);
  });

  it("clamps a negative treasury to zero", () => {
    expect(renderCard().commit("Treasury", "-3").factions[0].treasury).toBe(0);
  });

  it("clamps stability to 100", () => {
    expect(renderCard().commit("Stability", "140").factions[0].stability).toBe(100);
  });

  it("commits manpower", () => {
    expect(renderCard().commit("Manpower", "900").factions[0].manpower).toBe(900);
  });
});
