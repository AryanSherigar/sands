import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SplitArmyForm } from "../SplitArmyForm";

const TROOPS = { infantry: 100, cavalry: 30 };

describe("SplitArmyForm", () => {
  it("sends only the troops taken, and cannot split off nothing or everything", () => {
    const onSubmit = vi.fn();
    render(<SplitArmyForm troops={TROOPS} onSubmit={onSubmit} onCancel={vi.fn()} />);
    const submit = screen.getByRole("button", { name: "Split off" });

    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/cavalry/), { target: { value: "30" } });
    fireEvent.change(screen.getByLabelText(/infantry/), { target: { value: "100" } });
    expect(submit).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/infantry/), { target: { value: "0" } });
    fireEvent.click(submit);

    expect(onSubmit).toHaveBeenCalledWith({ cavalry: 30 });
  });

  it("never lets the player type more than an army holds", () => {
    render(<SplitArmyForm troops={TROOPS} onSubmit={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/cavalry/), { target: { value: "999" } });

    expect(screen.getByLabelText(/cavalry/)).toHaveValue(30);
  });
});
