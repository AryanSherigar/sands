import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { addFaction, readStrategyFields } from "../../../lib/strategyDocument";
import { setRelation, setVassalage } from "../../../lib/strategyStart";
import { StrategyRelationsPanel } from "../StrategyRelationsPanel";
import type { EditStrategyFields } from "../StrategyWorkspace.types";
import type { StrategyFields } from "../../../types/strategyDocument.types";

const pair = addFaction(addFaction(readStrategyFields({}), "Ashford"), "Carrow");

const renderPanel = (fields: StrategyFields) => {
  const onEdit = vi.fn<EditStrategyFields>();
  render(<StrategyRelationsPanel fields={fields} onEdit={onEdit} />);
  return { apply: () => onEdit.mock.calls.at(-1)![0](fields) };
};

describe("StrategyRelationsPanel", () => {
  it("sets a pair to war", () => {
    const { apply } = renderPanel(pair);
    fireEvent.change(screen.getByLabelText("Relation Ashford and Carrow"), { target: { value: "war" } });
    expect(apply().relations).toEqual([{ faction_a: "ashford", faction_b: "carrow", status: "war", vassalage: null }]);
  });

  it("stores an overlord on a peaceful pair", () => {
    const { apply } = renderPanel(pair);
    fireEvent.change(screen.getByLabelText("Overlord of Ashford and Carrow"), { target: { value: "ashford" } });
    expect(apply().relations[0].vassalage?.overlord_id).toBe("ashford");
  });

  it("hides the overlord choice while at war", () => {
    renderPanel(setRelation(pair, "ashford", "carrow", "war"));
    expect(screen.queryByLabelText("Overlord of Ashford and Carrow")).not.toBeInTheDocument();
  });

  it("shows a vassalage that is already set", () => {
    renderPanel(setVassalage(pair, "ashford", "carrow", "carrow"));
    expect(screen.getByLabelText("Overlord of Ashford and Carrow")).toHaveValue("carrow");
  });

  it("asks for a second faction when there is only one", () => {
    renderPanel(addFaction(readStrategyFields({}), "Ashford"));
    expect(screen.getByText("Add a second faction to set relations.")).toBeInTheDocument();
  });
});
