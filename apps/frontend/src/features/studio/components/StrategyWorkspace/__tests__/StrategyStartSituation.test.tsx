import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { addFaction, readStrategyFields, setRegionOwner } from "../../../lib/strategyDocument";
import type { StartPanelId } from "../../../lib/strategyPanels";
import { StrategyStartSituation } from "../StrategyStartSituation";

const fields = setRegionOwner(addFaction(addFaction(readStrategyFields({}), "Ashford"), "Carrow"), "north", "ashford");

const Harness = ({ initial = null }: { initial?: StartPanelId | null }) => {
  const [openPanel, setOpenPanel] = useState<StartPanelId | null>(initial);
  return <StrategyStartSituation fields={fields} regions={[]} openPanel={openPanel} onOpenPanel={setOpenPanel} onEdit={vi.fn()} />;
};

describe("StrategyStartSituation", () => {
  it("opens one panel at a time", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: /Relations/ }));
    expect(screen.getByRole("button", { name: /Relations/ })).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(screen.getByRole("button", { name: /Armies/ }));
    expect(screen.getByRole("button", { name: /Relations/ })).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("button", { name: /Armies/ })).toHaveAttribute("aria-expanded", "true");
  });

  it("shows a one-line summary on each header", () => {
    render(<Harness />);
    expect(screen.getByRole("button", { name: /Armies/ })).toHaveTextContent("1 army");
    expect(screen.getByRole("button", { name: /Relations/ })).toHaveTextContent("All at peace");
  });

  it("starts with the panel it is told to open", () => {
    render(<Harness initial="timeline" />);
    expect(screen.getByLabelText("End year")).toBeInTheDocument();
  });
});
