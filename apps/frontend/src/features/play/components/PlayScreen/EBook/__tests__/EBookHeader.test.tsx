import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlayStore } from "../../../../stores/play.store";
import { PlaythroughData } from "../../../../types/play.types";
import { EBookHeader } from "../EBookHeader";

vi.mock("../EBookNarrationVoiceControl", () => ({
  EBookNarrationVoiceControl: () => null,
}));

const hudHints = {
  clock: {
    path: "shift_minutes",
    hint: {
      kind: "clock" as const,
      label: "Shift",
      start: "23:00",
      format: "12h" as const,
    },
  },
  meters: [
    {
      path: "sanity",
      hint: {
        kind: "meter" as const,
        label: "Sanity",
        clamp_min: 0,
        clamp_max: 100,
      },
    },
  ],
};

const setPlaythrough = (enabledTools: string[]): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      scenario_title: "Night Desk",
      creator_name: "Someone",
      turns: [],
      enabled_tools: enabledTools,
      hud_hints: hudHints,
      state: { shift_minutes: 60, sanity: 70 },
    } as unknown as PlaythroughData,
  });
};

const renderHeader = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <EBookHeader
          onBack={() => {}}
          onOpenCodex={() => {}}
          onOpenChronicle={() => {}}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("EBookHeader status HUD", () => {
  beforeEach(() => {
    usePlayStore.setState({ playthrough: null });
  });

  it("shows no clock and no meter strip when the tool is off", () => {
    setPlaythrough([]);

    renderHeader();

    expect(screen.queryByText("Shift")).not.toBeInTheDocument();
    expect(screen.queryByRole("meter")).not.toBeInTheDocument();
  });

  it("shows the clock in the header and the meter in the strip when the tool is on", () => {
    setPlaythrough(["status_hud"]);

    renderHeader();

    expect(screen.getByText("Shift")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Sanity" })).toBeInTheDocument();
  });
});
