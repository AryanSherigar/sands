import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MeterBar } from "./MeterBar";

const base = {
  label: "Sanity",
  clampMin: 0,
  clampMax: 100,
  tierName: "Frayed",
  shouldAnimate: true,
};

describe("MeterBar", () => {
  it("exposes a meter with its value and tier", () => {
    render(<MeterBar {...base} value={62} />);

    const meter = screen.getByRole("meter", { name: "Sanity" });
    expect(meter).toHaveAttribute("aria-valuenow", "62");
    expect(meter).toHaveAttribute("aria-valuemin", "0");
    expect(meter).toHaveAttribute("aria-valuemax", "100");
    expect(meter).toHaveAttribute("aria-valuetext", "62, Frayed");
    expect(screen.getByText("Frayed")).toBeInTheDocument();
  });

  it("clamps the display at clampMin while the state may be lower", () => {
    render(<MeterBar {...base} value={-8} />);

    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "0");
    expect(screen.queryByText("-8")).not.toBeInTheDocument();
  });

  it("clamps the display at clampMax", () => {
    render(<MeterBar {...base} value={140} />);

    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "100");
  });

  it("omits the tier text when there is no tier", () => {
    render(<MeterBar {...base} tierName={null} value={50} />);

    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuetext", "50");
  });

  it("only animates the fill when allowed", () => {
    const { container, rerender } = render(<MeterBar {...base} value={50} />);
    expect(container.querySelector(".meter-fill-animated")).not.toBeNull();

    rerender(<MeterBar {...base} value={50} shouldAnimate={false} />);
    expect(container.querySelector(".meter-fill-animated")).toBeNull();
  });
});
