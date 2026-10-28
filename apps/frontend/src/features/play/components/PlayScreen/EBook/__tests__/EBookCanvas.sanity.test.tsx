import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { usePlayStore } from "../../../../stores/play.store";
import { PlaythroughData } from "../../../../types/play.types";
import { EBookCanvas } from "../EBookCanvas";

const meter = {
  path: "sanity",
  hint: {
    kind: "meter" as const,
    label: "Sanity",
    clamp_min: 0,
    clamp_max: 100,
    effects: { moderate_below: 50, critical_below: 25 },
  },
};

const STREAMING_TEXT = `${Array.from({ length: 500 }, (_, i) => `hallway${i}`).join(" ")} `;

const setPlaythrough = (
  sanity: number,
  enabledTools: string[] = ["status_hud", "atmosphere"],
): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      character_name: "Clerk",
      opening_premise: "The desk.",
      turns: [],
      story_cards: [],
      key_facts: [],
      entities: [],
      enabled_tools: enabledTools,
      hud_hints: { meters: [meter] },
      state: { sanity },
    } as unknown as PlaythroughData,
  });
};

const rootOf = (container: HTMLElement): HTMLElement =>
  container.querySelector("main") as HTMLElement;

describe("EBookCanvas sanity bands", () => {
  beforeEach(() => {
    Element.prototype.scrollTo = vi.fn();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    usePlayStore.setState({
      is_narrating: false,
      streaming_text: "",
      reader_font_override: null,
    });
  });

  it.each([
    [80, null],
    [40, "moderate"],
    [10, "critical"],
    [-8, "critical"],
  ])("sets data-sanity for sanity %i", (sanity, expected) => {
    setPlaythrough(sanity);

    const { container } = render(<EBookCanvas />);

    expect(rootOf(container).getAttribute("data-sanity")).toBe(expected);
  });

  it("has no band without the atmosphere tool, however low the sanity", () => {
    setPlaythrough(5, ["status_hud"]);

    const { container } = render(<EBookCanvas />);

    expect(rootOf(container).hasAttribute("data-sanity")).toBe(false);
  });

  it("drops the band under reduced sensory effects", () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    setPlaythrough(5);

    const { container } = render(<EBookCanvas />);

    expect(rootOf(container).hasAttribute("data-sanity")).toBe(false);
  });

  it("distorts the streaming paragraph while a band is active", () => {
    setPlaythrough(10);
    act(() => {
      usePlayStore.setState({ is_narrating: true, streaming_text: STREAMING_TEXT });
    });

    const { container } = render(<EBookCanvas />);

    expect(container.querySelectorAll(".font-eerie").length).toBeGreaterThan(5);
    expect(container.textContent).toContain("hallway499");
  });

  it("leaves the streaming paragraph a plain <p> with no band", () => {
    setPlaythrough(90);
    act(() => {
      usePlayStore.setState({ is_narrating: true, streaming_text: STREAMING_TEXT });
    });

    const { container } = render(<EBookCanvas />);

    expect(container.querySelectorAll(".font-eerie")).toHaveLength(0);
    const paragraph = screen.getByText(/hallway0 hallway1/);
    expect(paragraph.tagName).toBe("P");
    expect(paragraph.className).toBe("");
  });

  it("updates streaming distortion when sensory effects are reduced", () => {
    setPlaythrough(10);
    usePlayStore.setState({ is_narrating: true, streaming_text: STREAMING_TEXT });
    const { container } = render(<EBookCanvas />);
    expect(container.querySelectorAll(".font-eerie").length).toBeGreaterThan(5);

    act(() => useReaderPreferencesStore.setState({ reduceSensoryEffects: true }));

    expect(rootOf(container).hasAttribute("data-sanity")).toBe(false);
    expect(container.querySelectorAll(".font-eerie")).toHaveLength(0);
    expect(screen.getByText(/hallway0 hallway1/).className).toBe("");
  });
});
