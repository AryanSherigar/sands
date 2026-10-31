import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyNumberField } from "../StrategyNumberField";

describe("StrategyNumberField", () => {
  it("selects the whole value on focus so typing replaces it", () => {
    render(<StrategyNumberField label="Wealth" value={50} onCommit={vi.fn()} />);
    const input = screen.getByLabelText<HTMLInputElement>("Wealth");
    fireEvent.focus(input);
    expect([input.selectionStart, input.selectionEnd]).toEqual([0, 2]);
  });

  it("commits the clamped value on Enter", () => {
    const onCommit = vi.fn();
    render(<StrategyNumberField label="Stability" value={60} max={100} onCommit={onCommit} />);
    const input = screen.getByLabelText("Stability");
    fireEvent.change(input, { target: { value: "140" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onCommit).toHaveBeenCalledWith(100);
  });
});
