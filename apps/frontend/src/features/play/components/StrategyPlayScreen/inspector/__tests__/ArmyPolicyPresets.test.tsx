import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ArmyPolicyPresets } from "../ArmyPolicyPresets";

describe("ArmyPolicyPresets", () => {
  it("shows the army's current presets, defaulting to the balanced ones", () => {
    render(<ArmyPolicyPresets armyId="army-1" reservePolicy="reinforce_on_pressure" />);

    expect(screen.getByLabelText("If hard pressed")).toHaveValue("balanced");
    expect(screen.getByLabelText("Reserves")).toHaveValue("reinforce_on_pressure");
  });

  it("sends only the preset that changed", () => {
    const onAction = vi.fn();
    render(<ArmyPolicyPresets armyId="army-1" onAction={onAction} />);

    fireEvent.change(screen.getByLabelText("If hard pressed"), { target: { value: "preserve" } });

    expect(onAction).toHaveBeenCalledWith({
      type: "set_army_policy",
      armyId: "army-1",
      policy: { withdrawal_policy: "preserve" },
    });
  });
});
