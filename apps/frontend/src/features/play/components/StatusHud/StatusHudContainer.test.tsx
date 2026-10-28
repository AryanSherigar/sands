import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { StatusHudContainer } from "./StatusHudContainer";

const clockHint = {
  path: "shift_minutes",
  hint: {
    kind: "clock" as const,
    label: "Shift",
    start: "23:00",
    format: "12h" as const,
  },
};

const setPlaythrough = (overrides: Partial<PlaythroughData>): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["status_hud"],
      hud_hints: { clock: clockHint, meters: [] },
      state: { shift_minutes: 420 },
      ...overrides,
    } as PlaythroughData,
  });
};

describe("StatusHudContainer", () => {
  beforeEach(() => {
    usePlayStore.setState({ playthrough: null });
  });

  it("shows the shift clock from the state", () => {
    setPlaythrough({});

    render(<StatusHudContainer />);

    expect(screen.getByText("06:00 AM")).toBeInTheDocument();
    expect(screen.getByText("Shift")).toBeInTheDocument();
  });

  it("follows the state when it changes", () => {
    setPlaythrough({});
    render(<StatusHudContainer />);

    act(() => {
      setPlaythrough({ state: { shift_minutes: 0 } });
    });

    expect(screen.getByText("11:00 PM")).toBeInTheDocument();
  });

  it("shows nothing when the tool is off, even with hints in the schema", () => {
    setPlaythrough({ enabled_tools: [] });

    const { container } = render(<StatusHudContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows nothing when the scenario authored no clock", () => {
    setPlaythrough({ hud_hints: { meters: [] } });

    const { container } = render(<StatusHudContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("stays hidden until the clock has a value", () => {
    setPlaythrough({ state: {} });

    const { container } = render(<StatusHudContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("stays hidden for a non-numeric clock value", () => {
    setPlaythrough({ state: { shift_minutes: "noon" } });

    const { container } = render(<StatusHudContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing without a playthrough", () => {
    const { container } = render(<StatusHudContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  describe("glitch", () => {
    const glitchHints = {
      clock: {
        ...clockHint,
        hint: {
          ...clockHint.hint,
          format: "24h" as const,
          glitch: { source: "sanity", below: 25, chance: 1 },
        },
      },
      meters: [],
    };

    beforeEach(() => {
      useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    });

    it("shows an impossible minute while the source meter is low", () => {
      setPlaythrough({
        hud_hints: glitchHints,
        state: { shift_minutes: 180, sanity: 10 },
      });

      render(<StatusHudContainer />);

      expect(screen.getByRole("group", { name: /^Shift 02:(6|7|8|9)\d$/ })).toBeInTheDocument();
    });

    it("shows the true time while the source meter is healthy", () => {
      setPlaythrough({
        hud_hints: glitchHints,
        state: { shift_minutes: 180, sanity: 80 },
      });

      render(<StatusHudContainer />);

      expect(screen.getByText("02:00")).toBeInTheDocument();
    });

    it("renders the same glitched time on every render", () => {
      setPlaythrough({
        hud_hints: glitchHints,
        state: { shift_minutes: 180, sanity: 10 },
      });
      const first = render(<StatusHudContainer />);
      const firstText = first.container.textContent;
      first.unmount();

      const second = render(<StatusHudContainer />);

      expect(second.container.textContent).toBe(firstText);
    });

    it("keeps the wrong time but drops the animation under reduced effects", () => {
      useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
      setPlaythrough({
        hud_hints: glitchHints,
        state: { shift_minutes: 180, sanity: 10 },
      });

      const { container } = render(<StatusHudContainer />);

      expect(container.textContent).toMatch(/02:(6|7|8|9)\d/);
      expect(container.querySelector('[data-glitched="true"]')).toBeNull();
    });
  });
});
