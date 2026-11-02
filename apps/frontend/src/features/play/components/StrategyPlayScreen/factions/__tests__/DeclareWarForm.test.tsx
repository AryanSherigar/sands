import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DeclareWarForm } from "../DeclareWarForm";

const GROUNDS = [{ id: "g1", kind: "claim" as const, target_faction_id: "ash", region_id: "r1" }];

describe("DeclareWarForm", () => {
  it("offers the usable cause first and submits its id", () => {
    const onSubmit = vi.fn();
    render(<DeclareWarForm targetName="Ashford" grounds={GROUNDS} regionNames={{ r1: "Greenford" }} onSubmit={onSubmit} onCancel={vi.fn()} />);

    expect(screen.getByRole("option", { name: "A claim: Greenford" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Declare war" }));

    expect(onSubmit).toHaveBeenCalledWith("g1");
  });

  it("can declare with no cause", () => {
    const onSubmit = vi.fn();
    render(<DeclareWarForm targetName="Ashford" grounds={GROUNDS} onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Your cause"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Declare war" }));

    expect(onSubmit).toHaveBeenCalledWith(null);
  });
});
