import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ArmyRosterView } from "../ArmyRosterView";
import type { ArmyView } from "../../../../types/simulation.types";

const mockArmy: ArmyView = {
  army_id: "a-1",
  owner_id: "f-1",
  location_id: "r-1",
  pay_level: "full",
  commander_name: "Sir Aldric",
  troops: { infantry: 1000 },
};

describe("ArmyRosterView", () => {
  it("shows pay toggle for own army", () => {
    render(<ArmyRosterView army={mockArmy} isOwnArmy onAction={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Full Pay/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reduced Pay/i })).toBeInTheDocument();
  });

  it("hides pay toggle for enemy army", () => {
    render(<ArmyRosterView army={mockArmy} isOwnArmy={false} onAction={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /Full Pay/i })).not.toBeInTheDocument();
  });

  it("marks the current pay level as active", () => {
    render(<ArmyRosterView army={mockArmy} isOwnArmy onAction={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Full Pay/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: /Reduced Pay/i })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("calls onAction with set_pay when inactive pay level is clicked", () => {
    const onAction = vi.fn();
    render(<ArmyRosterView army={mockArmy} isOwnArmy onAction={onAction} />);
    fireEvent.click(screen.getByRole("button", { name: /Reduced Pay/i }));
    expect(onAction).toHaveBeenCalledWith({
      type: "set_pay",
      armyId: "a-1",
      payLevel: "reduced",
    });
  });

  it("does not call onAction when the already-active pay level is clicked", () => {
    const onAction = vi.fn();
    render(<ArmyRosterView army={mockArmy} isOwnArmy onAction={onAction} />);
    fireEvent.click(screen.getByRole("button", { name: /Full Pay/i }));
    expect(onAction).not.toHaveBeenCalled();
  });

  it("shows Declare War button for foreign host when not at war", () => {
    const onAction = vi.fn();
    render(<ArmyRosterView army={mockArmy} isOwnArmy={false} isAtWar={false} onAction={onAction} />);
    const button = screen.getByRole("button", { name: /Declare War/i });
    expect(button).toBeInTheDocument();
    fireEvent.click(button);
    expect(onAction).toHaveBeenCalledWith({
      type: "declare_war",
      targetFactionId: "f-1",
    });
  });

  it("hides Declare War button for foreign host when at war", () => {
    render(<ArmyRosterView army={mockArmy} isOwnArmy={false} isAtWar={true} onAction={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /Declare War/i })).not.toBeInTheDocument();
  });

  it("offers Besiege only when the army can besiege", () => {
    const onAction = vi.fn();
    const { rerender } = render(<ArmyRosterView army={mockArmy} isOwnArmy onAction={onAction} />);
    expect(screen.queryByRole("button", { name: "Besiege" })).not.toBeInTheDocument();

    rerender(<ArmyRosterView army={mockArmy} isOwnArmy canBesiege onAction={onAction} />);
    fireEvent.click(screen.getByRole("button", { name: "Besiege" }));
    expect(onAction).toHaveBeenCalledWith({ type: "besiege", armyId: "a-1" });
  });
});
