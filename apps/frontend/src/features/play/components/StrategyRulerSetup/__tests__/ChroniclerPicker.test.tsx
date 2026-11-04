import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChroniclerPicker } from "../ChroniclerPicker";
import { buildPlayerRulerPayload } from "../buildPlayerRulerPayload";

describe("ChroniclerPicker", () => {
  it("shows all five chroniclers with Brother Lucan selected by default", () => {
    render(<ChroniclerPicker selectedId="lucan" onSelect={vi.fn()} />);
    expect(screen.getAllByRole("radio")).toHaveLength(5);
    expect(
      screen.getByRole("radio", { name: /Brother Lucan/i }).getAttribute("aria-checked"),
    ).toBe("true");
    expect(
      screen.getByRole("radio", { name: /Vaelen the Scorned/i }).getAttribute("aria-checked"),
    ).toBe("false");
  });

  it("reports the chronicler the player picks", () => {
    const onSelect = vi.fn();
    render(<ChroniclerPicker selectedId="lucan" onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("radio", { name: /Vaelen the Scorned/i }));
    expect(onSelect).toHaveBeenCalledWith("vaelen");
  });

  it("says the choice is permanent", () => {
    render(<ChroniclerPicker selectedId="lucan" onSelect={vi.fn()} />);
    expect(
      screen.getByText("Your chronicler is chosen once and writes your whole story."),
    ).toBeDefined();
  });
});

describe("buildPlayerRulerPayload", () => {
  it("sends chronicler_id vaelen when Vaelen is chosen", () => {
    const payload = buildPlayerRulerPayload({
      name: "Aldric",
      epithet: "",
      portraitUrl: "",
      traitIds: ["cautious", "honorable"],
      ambitionIds: ["ambition_peace"],
      backstory: "",
      chroniclerId: "vaelen",
    });
    expect(payload.chronicler_id).toBe("vaelen");
    expect(payload.epithet).toBeNull();
  });
});
