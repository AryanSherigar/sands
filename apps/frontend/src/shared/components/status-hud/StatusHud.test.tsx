import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusHud } from "./StatusHud";

const meter = {
  label: "Sanity",
  value: 80,
  clampMin: 0,
  clampMax: 100,
  shouldAnimate: false,
};

describe("StatusHud", () => {
  it("renders every meter and the tier", () => {
    render(
      <StatusHud
        meters={[meter, { ...meter, label: "Battery", value: 20 }]}
        tier={{ label: "Tension", options: ["a", "b"], value: "a" }}
      />,
    );

    expect(screen.getAllByRole("meter")).toHaveLength(2);
    expect(screen.getByRole("group", { name: "Tension a" })).toBeInTheDocument();
  });

  it("renders without a tier", () => {
    render(<StatusHud meters={[meter]} />);

    expect(screen.getByRole("meter", { name: "Sanity" })).toBeInTheDocument();
  });
});
