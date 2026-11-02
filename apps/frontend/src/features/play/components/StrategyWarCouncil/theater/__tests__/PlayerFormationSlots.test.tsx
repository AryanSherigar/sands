import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PlayerFormationSlots } from "../PlayerFormationSlots";

describe("PlayerFormationSlots", () => {
  it("renders 3 formation slots and highlights tactic anchor", () => {
    const handleSelect = vi.fn();
    render(
      <PlayerFormationSlots
        formation="defensive"
        anchorSlot="center"
        onSelectSlot={handleSelect}
        troops={{ infantry: 1400, cavalry: 300, archers_siege: 650 }}
        morale={92}
      />,
    );

    expect(screen.getByText("Center Vanguard • Ford")).toBeInTheDocument();
    expect(screen.getByText("Tactic Anchor")).toBeInTheDocument();
    expect(screen.getByText("Left Flank • Ashwood")).toBeInTheDocument();
    expect(screen.getByText("Right Flank • Mud Meadow")).toBeInTheDocument();

    const leftSlot = screen.getByText("Left Flank • Ashwood").closest(".formation-slot");
    fireEvent.click(leftSlot!);
    expect(handleSelect).toHaveBeenCalledWith("left");
  });
});
