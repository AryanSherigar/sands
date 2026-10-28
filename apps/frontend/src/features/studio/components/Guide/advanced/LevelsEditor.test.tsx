import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React, { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { MeterTier } from "@/shared/types/display-hints.types";
import { LevelsEditor } from "./LevelsEditor";

const Harness: React.FC<{ initial: MeterTier[]; onTiers: (tiers: MeterTier[]) => void }> = ({ initial, onTiers }) => {
  const [tiers, setTiers] = useState(initial);
  return (
    <LevelsEditor
      tiers={tiers}
      onChange={(next) => {
        setTiers(next);
        onTiers(next);
      }}
    />
  );
};

const START: MeterTier[] = [{ name: "High", min: 7 }, { name: "Low" }];

describe("LevelsEditor", () => {
  it("keeps the rows where they are while a threshold is typed and sorts them on blur", async () => {
    const user = userEvent.setup();
    const onTiers = vi.fn();
    render(<Harness initial={[{ name: "High", min: 7 }, { name: "Mid", min: 4 }, { name: "Low" }]} onTiers={onTiers} />);
    const second = screen.getByLabelText("Level 2 from");
    await user.clear(second);
    await user.type(second, "10");
    expect(screen.getByLabelText("Level 2 name")).toHaveValue("Mid");
    expect(second).toHaveValue("10");
    await user.tab();
    expect(screen.getByLabelText("Level 1 name")).toHaveValue("Mid");
    expect(onTiers.mock.calls.at(-1)?.[0]).toEqual([{ name: "Mid", min: 10 }, { name: "High", min: 7 }, { name: "Low" }]);
  });

  it("does not send equal thresholds and says why", async () => {
    const user = userEvent.setup();
    const onTiers = vi.fn();
    render(<Harness initial={[{ name: "High", min: 7 }, { name: "Mid", min: 4 }]} onTiers={onTiers} />);
    const second = screen.getByLabelText("Level 2 from");
    await user.clear(second);
    await user.type(second, "7");
    expect(screen.getByRole("alert")).toHaveTextContent("Each level needs its own threshold");
    expect(onTiers).not.toHaveBeenCalledWith([{ name: "High", min: 7 }, { name: "Mid", min: 7 }]);
  });

  it("adds levels with distinct thresholds when Add a level is pressed twice", async () => {
    const user = userEvent.setup();
    const onTiers = vi.fn();
    render(<Harness initial={START} onTiers={onTiers} />);
    await user.click(screen.getByRole("button", { name: "+ Add a level" }));
    await user.click(screen.getByRole("button", { name: "+ Add a level" }));
    const mins = (onTiers.mock.calls.at(-1)?.[0] as MeterTier[]).flatMap((tier) => (tier.min === undefined ? [] : [tier.min]));
    expect(new Set(mins).size).toBe(mins.length);
    expect(mins).toEqual([...mins].sort((first, second) => second - first));
  });

  it("allows only one level without a threshold", async () => {
    const user = userEvent.setup();
    const onTiers = vi.fn();
    render(<Harness initial={[{ name: "High", min: 7 }, { name: "Mid", min: 4 }, { name: "Low" }]} onTiers={onTiers} />);
    await user.clear(screen.getByLabelText("Level 1 from"));
    expect(screen.getByRole("alert")).toHaveTextContent("Only one level can have no threshold");
    expect(onTiers).not.toHaveBeenCalled();
  });
});
