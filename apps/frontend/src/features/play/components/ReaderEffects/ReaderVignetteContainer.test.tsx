import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { ReaderVignetteContainer } from "./ReaderVignetteContainer";

const tierHints = {
  meters: [],
  tier: {
    path: "tension_tier",
    hint: { kind: "tier" as const, label: "Tension" },
    options: ["uneasy", "tense", "dread", "breaking"],
  },
};

const setPlaythrough = (
  tier: string,
  overrides: Partial<PlaythroughData> = {},
): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["status_hud", "atmosphere"],
      hud_hints: tierHints,
      state: { tension_tier: tier },
      ...overrides,
    } as unknown as PlaythroughData,
  });
};

describe("ReaderVignetteContainer", () => {
  beforeEach(() => {
    usePlayStore.setState({ playthrough: null, ebook_theme: "dark-velvet" });
  });

  it("scales the vignette with the tier up to 0.55", () => {
    setPlaythrough("breaking");
    const { container } = render(<ReaderVignetteContainer />);

    expect(Number(container.querySelector("rect")?.getAttribute("fill-opacity"))).toBeCloseTo(0.55);
  });

  it("is invisible at the first tier but still mounted", () => {
    setPlaythrough("uneasy");
    const { container } = render(<ReaderVignetteContainer />);

    expect(container.querySelector("rect")).toHaveAttribute("fill-opacity", "0");
  });

  it("follows the reader theme", () => {
    usePlayStore.setState({ ebook_theme: "antique-sepia" });
    setPlaythrough("tense");
    const { container } = render(<ReaderVignetteContainer />);

    expect(container.querySelector("svg")).toHaveAttribute("data-theme", "antique-sepia");
  });

  it("renders nothing without a tier field", () => {
    setPlaythrough("tense", { hud_hints: { meters: [] } });
    const { container } = render(<ReaderVignetteContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing unless atmosphere and status_hud are both on", () => {
    setPlaythrough("breaking", { enabled_tools: ["status_hud"] });
    const { container } = render(<ReaderVignetteContainer />);

    expect(container).toBeEmptyDOMElement();
  });
});
