import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RangePicker } from "../RangePicker";

describe("RangePicker", () => {
  it("marks the current range and reports a new choice", async () => {
    const handleChange = vi.fn();
    render(<RangePicker value="30d" onChange={handleChange} />);

    expect(screen.getByRole("radio", { name: "30d" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "All time" })).toHaveAttribute(
      "aria-checked",
      "false",
    );

    await userEvent.click(screen.getByRole("radio", { name: "7d" }));
    expect(handleChange).toHaveBeenCalledWith("7d");
  });
});
