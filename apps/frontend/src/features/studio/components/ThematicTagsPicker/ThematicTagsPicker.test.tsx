import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { MAX_THEMATIC_TAGS } from "@/shared/constants/thematic-tags";
import { ThematicTagsPicker } from "./ThematicTagsPicker";

const Harness: React.FC<{ initial?: string[] }> = ({ initial = [] }) => {
  const [selected, setSelected] = useState<string[]>(initial);
  return (
    <>
      <ThematicTagsPicker selected={selected} onChange={setSelected} />
      <output aria-label="selection">{selected.join(",")}</output>
    </>
  );
};

const selection = (): string =>
  screen.getByLabelText("selection").textContent ?? "";

describe("ThematicTagsPicker", () => {
  it("toggles tags on and off and keeps the order they were chosen in", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Romance" }));
    await user.click(screen.getByRole("button", { name: "Cozy tone" }));
    expect(selection()).toBe("romance,cozy-tone");

    await user.click(screen.getByRole("button", { name: "Romance" }));
    expect(selection()).toBe("cozy-tone");
  });

  it("shows how many are chosen and marks selected tags as pressed", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Romance" }));

    expect(screen.getByText(`1 / ${MAX_THEMATIC_TAGS}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Romance" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("stops offering more tags at the maximum but still lets you deselect", async () => {
    const user = userEvent.setup();
    const full = [
      "romance",
      "cozy-tone",
      "investigation",
      "dark-humour",
      "found-family",
    ];
    render(<Harness initial={full} />);

    expect(screen.getByRole("button", { name: "Horror themes" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Romance" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Romance" }));

    expect(screen.getByRole("button", { name: "Horror themes" })).toBeEnabled();
  });
});
