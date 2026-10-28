import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ShiftClockBadge } from "./ShiftClockBadge";

describe("ShiftClockBadge", () => {
  it("shows the label and the time", () => {
    render(<ShiftClockBadge label="Shift" time="11:42 PM" />);

    expect(screen.getByText("Shift")).toBeInTheDocument();
    expect(screen.getByText("11:42 PM")).toBeInTheDocument();
  });

  it("exposes one readable name for assistive technology", () => {
    render(<ShiftClockBadge label="Shift" time="11:42 PM" />);

    expect(screen.getByRole("group", { name: "Shift 11:42 PM" })).toBeInTheDocument();
  });
});

describe("ShiftClockBadge glitch", () => {
  it("marks the time as glitched only when it should animate", () => {
    const { rerender } = render(
      <ShiftClockBadge label="Shift" time="03:84 AM" isGlitched shouldAnimate />,
    );
    expect(screen.getByText("03:84 AM")).toHaveAttribute("data-glitched", "true");

    rerender(
      <ShiftClockBadge
        label="Shift"
        time="03:84 AM"
        isGlitched
        shouldAnimate={false}
      />,
    );
    expect(screen.getByText("03:84 AM")).toHaveAttribute("data-glitched", "false");
  });
});
