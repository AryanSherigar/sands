import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SegmentedControl } from "../components/SegmentedControl/SegmentedControl";

const OPTIONS = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
];

describe("SegmentedControl", () => {
  it("marks the selected option and reports changes", () => {
    const handleChange = vi.fn();
    render(
      <SegmentedControl
        ariaLabel="Filter"
        options={OPTIONS}
        value="all"
        onChange={handleChange}
      />,
    );
    expect(screen.getByRole("radio", { name: "All" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    fireEvent.click(screen.getByRole("radio", { name: "Active" }));
    expect(handleChange).toHaveBeenCalledWith("active");
  });

  it("exposes a labelled radiogroup", () => {
    render(
      <SegmentedControl
        ariaLabel="Filter"
        options={OPTIONS}
        value="all"
        onChange={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("radiogroup", { name: "Filter" }),
    ).toBeInTheDocument();
  });

  it("uses a roving tabindex and arrow keys move the selection", () => {
    const handleChange = vi.fn();
    render(
      <SegmentedControl
        ariaLabel="Filter"
        options={OPTIONS}
        value="all"
        onChange={handleChange}
      />,
    );
    expect(screen.getByRole("radio", { name: "All" })).toHaveAttribute(
      "tabindex",
      "0",
    );
    expect(screen.getByRole("radio", { name: "Active" })).toHaveAttribute(
      "tabindex",
      "-1",
    );
    fireEvent.keyDown(screen.getByRole("radio", { name: "All" }), {
      key: "ArrowRight",
    });
    expect(handleChange).toHaveBeenLastCalledWith("active");
    fireEvent.keyDown(screen.getByRole("radio", { name: "All" }), {
      key: "ArrowUp",
    });
    expect(handleChange).toHaveBeenLastCalledWith("active");
  });
});
