import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { StatusHudStripContainer } from "./StatusHudStripContainer";

const hints = {
  meters: [
    {
      path: "sanity",
      hint: {
        kind: "meter" as const,
        label: "Sanity",
        clamp_min: 0,
        clamp_max: 100,
        tiers: [{ name: "Clear", min: 50 }, { name: "Unraveling" }],
      },
    },
  ],
  tier: {
    path: "tension_tier",
    hint: { kind: "tier" as const, label: "Tension" },
    options: ["uneasy", "tense"],
  },
};

const setPlaythrough = (overrides: Partial<PlaythroughData>): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["status_hud"],
      hud_hints: hints,
      state: { sanity: 80, tension_tier: "uneasy" },
      ...overrides,
    } as PlaythroughData,
  });
};

describe("StatusHudStripContainer", () => {
  beforeEach(() => {
    usePlayStore.setState({ playthrough: null });
  });

  it("shows the meter with its tier and the tension pips", () => {
    setPlaythrough({});

    render(<StatusHudStripContainer />);

    expect(screen.getByRole("meter", { name: "Sanity" })).toHaveAttribute(
      "aria-valuetext",
      "80, Clear",
    );
    expect(screen.getByRole("group", { name: "Tension uneasy" })).toBeInTheDocument();
  });

  it("clamps a meter whose state is below its floor", () => {
    setPlaythrough({ state: { sanity: -8, tension_tier: "tense" } });

    render(<StatusHudStripContainer />);

    const meter = screen.getByRole("meter", { name: "Sanity" });
    expect(meter).toHaveAttribute("aria-valuenow", "0");
    expect(meter).toHaveAttribute("aria-valuetext", "0, Unraveling");
  });

  it("follows the state when it changes", () => {
    setPlaythrough({});
    render(<StatusHudStripContainer />);

    act(() => {
      usePlayStore.setState((current) => ({
        playthrough: {
          ...(current.playthrough as PlaythroughData),
          state: { sanity: 30, tension_tier: "tense" },
        },
      }));
    });

    expect(screen.getByRole("group", { name: "Tension tense" })).toBeInTheDocument();
  });

  it("shows nothing when the tool is off, even with hints", () => {
    setPlaythrough({ enabled_tools: [] });

    const { container } = render(<StatusHudStripContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows nothing when the scenario declared no meter or tier", () => {
    setPlaythrough({ hud_hints: { meters: [] } });

    const { container } = render(<StatusHudStripContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows nothing until a value exists", () => {
    setPlaythrough({ state: {} });

    const { container } = render(<StatusHudStripContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing without a playthrough", () => {
    const { container } = render(<StatusHudStripContainer />);

    expect(container).toBeEmptyDOMElement();
  });
});
