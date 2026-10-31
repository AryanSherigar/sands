import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StateMutationRow } from "./StateMutationRow";

describe("scene character rule", () => {
  it("writes a character id list instead of a text value", async () => {
    const onChange = vi.fn();
    render(<ul><StateMutationRow index={0} total={1} mutation={{ path: "scene_character_ids", op: "set", value: [] }} characters={[{ id: "asha", name: "Asha" }]} onChange={onChange} onMove={vi.fn()} onRemove={vi.fn()} /></ul>);
    await userEvent.setup().click(screen.getByRole("checkbox", { name: "Asha" }));
    expect(onChange).toHaveBeenCalledWith(0, { path: "scene_character_ids", op: "set", value: ["asha"] });
  });
});
