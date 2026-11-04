import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { addFaction, readStrategyFields, setRegionOwner } from "../../../lib/strategyDocument";
import { StrategyPresetPicker } from "../StrategyPresetPicker";
import type { EditStrategyFields } from "../StrategyWorkspace.types";
import type { StrategyFields } from "../../../types/strategyDocument.types";

const unarmed = addFaction(addFaction(readStrategyFields({}), "Ashford"), "Carrow");
const armed: StrategyFields = setRegionOwner(unarmed, "north", "ashford");

const renderPicker = (fields: StrategyFields) => {
  const onEdit = vi.fn<EditStrategyFields>();
  render(<StrategyPresetPicker fields={fields} regions={[]} onEdit={onEdit} />);
  return onEdit;
};

afterEach(() => vi.restoreAllMocks());

describe("StrategyPresetPicker", () => {
  it("applies the border war preset directly when nothing would be overwritten", () => {
    const onEdit = renderPicker(unarmed);
    fireEvent.click(screen.getByRole("button", { name: "Border war" }));
    expect(onEdit.mock.calls.at(-1)![0](unarmed).relations[0].status).toBe("war");
  });

  it("asks in an in-app dialog before overwriting and does nothing on cancel", () => {
    const confirmSpy = vi.spyOn(window, "confirm");
    const onEdit = renderPicker(armed);
    fireEvent.click(screen.getByRole("button", { name: "Peaceful start" }));
    expect(screen.getByText("This replaces your armies and relations. Continue?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onEdit).not.toHaveBeenCalled();
    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it("applies after the creator confirms", () => {
    const onEdit = renderPicker(armed);
    fireEvent.click(screen.getByRole("button", { name: "Peaceful start" }));
    fireEvent.click(screen.getByRole("button", { name: "Replace" }));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });
});
