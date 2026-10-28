import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { usePlayStore } from "../../../../stores/play.store";
import { PlaythroughData, TurnLogItem } from "../../../../types/play.types";
import { EBookCanvas } from "../EBookCanvas";

const scrollTo = vi.fn();
const stopGeneration = vi.fn();
const historicalTurn: TurnLogItem = {
  id: "turn-1",
  turn_number: 1,
  action_mode: "do",
  action_text: "Continue the story.",
  narration_text: "Marlowe waits beside the desk.",
  created_at: "2026-10-27T12:00:00Z",
};
const storyCard = {
  id: "card-1",
  title: "Marlowe",
  category: "character",
  content: "The keeper of the archive.",
};
const playthrough = {
  playthrough_id: "pt-1",
  character_name: "Clerk",
  opening_premise: "The archive opens.",
  turns: [historicalTurn],
  story_cards: [storyCard],
  key_facts: [],
  entities: [],
  enabled_tools: [],
} as unknown as PlaythroughData;

describe("EBookCanvas streaming", () => {
  beforeEach(() => {
    scrollTo.mockClear();
    stopGeneration.mockClear();
    server.use(
      http.get("*/v1/users/me", () => HttpResponse.json({ voice_output_enabled: false })),
      http.get("*/v1/alpha/config", () => HttpResponse.json({ is_alpha_mode: false })),
    );
    Element.prototype.scrollTo = scrollTo;
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    usePlayStore.setState({
      playthrough,
      is_narrating: true,
      streaming_text: "",
      last_submitted_action: "Open the ledger.",
      active_mode: "do",
      reader_font_override: null,
      reader_font_size: "medium",
      playing_audio_turn_id: null,
      stopGeneration,
    });
  });

  it("replaces the waiting message with successive narration and scrolls instantly", () => {
    render(<EBookCanvas />, { wrapper: createQueryWrapper() });
    expect(screen.getByText("The narrator considers your choices...")).toBeInTheDocument();
    expect(screen.getByText("Inscribing Chapter 2...")).toBeInTheDocument();
    expect(screen.getByText(/"Open the ledger\."/)).toBeInTheDocument();
    scrollTo.mockClear();

    act(() => usePlayStore.setState({ streaming_text: "The pages" }));
    expect(screen.queryByText("The narrator considers your choices...")).not.toBeInTheDocument();
    expect(screen.getByText("The pages")).toBeInTheDocument();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: "auto" });
    scrollTo.mockClear();

    act(() => usePlayStore.setState({ streaming_text: "The pages rustle." }));
    expect(screen.getByText("The pages rustle.")).toBeInTheDocument();
    expect(screen.getByText(/waits beside the desk/)).toBeInTheDocument();
    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: "auto" });
  });

  it("keeps Continue silent and exposes the Stop control", async () => {
    usePlayStore.setState({ last_submitted_action: "Continue the story." });
    render(<EBookCanvas />, { wrapper: createQueryWrapper() });
    expect(screen.queryByText(/"Continue the story\."/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Stop" }));
    expect(stopGeneration).toHaveBeenCalledTimes(1);
  });

  it("moves completed narration into history and scrolls smoothly", () => {
    usePlayStore.setState({ streaming_text: "The pages rustle." });
    render(<EBookCanvas />, { wrapper: createQueryWrapper() });
    scrollTo.mockClear();

    act(() => usePlayStore.setState({
      is_narrating: false,
      streaming_text: "",
      playthrough: {
        ...playthrough,
        turns: [...playthrough.turns, {
          ...historicalTurn,
          id: "turn-2",
          turn_number: 2,
          narration_text: "The pages rustle.",
        }],
      },
    }));

    expect(screen.getAllByText("The pages rustle.")).toHaveLength(1);
    expect(screen.getByText("Chapter 2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stop" })).not.toBeInTheDocument();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: "smooth" });
  });

  it("updates typography in historical and streaming narration", () => {
    usePlayStore.setState({ streaming_text: "The pages rustle." });
    render(<EBookCanvas />, { wrapper: createQueryWrapper() });

    act(() => usePlayStore.setState({
      reader_font_override: "special-elite",
      reader_font_size: "large",
    }));

    expect(screen.getByText(/waits beside the desk/).closest("p")).toHaveClass(
      "font-narration-special-elite", "text-[22px]",
    );
    expect(screen.getByText("The pages rustle.").parentElement).toHaveClass(
      "font-narration-special-elite", "text-[22px]",
    );
  });

  it("mounts live narration when a playthrough becomes available", () => {
    usePlayStore.setState({ playthrough: null, is_narrating: false });
    render(<EBookCanvas />, { wrapper: createQueryWrapper() });
    expect(screen.queryByText("Inscribing Chapter 2...")).not.toBeInTheDocument();

    act(() => usePlayStore.setState({ playthrough, is_narrating: true }));

    expect(screen.getByText("Inscribing Chapter 2...")).toBeInTheDocument();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: "auto" });
  });

  it("updates historical distortion when sensory effects are reduced", () => {
    const narration = Array.from({ length: 500 }, (_, index) => `hallway${index}`).join(" ");
    usePlayStore.setState({ playthrough: {
      ...playthrough,
      turns: [{ ...historicalTurn, narration_text: narration }],
      enabled_tools: ["status_hud", "atmosphere"],
      state: { sanity: 10 },
      hud_hints: { meters: [{ path: "sanity", hint: {
        kind: "meter", label: "Sanity", clamp_min: 0, clamp_max: 100,
        effects: { moderate_below: 50, critical_below: 25 },
      } }] },
    } });
    const { container } = render(<EBookCanvas />, { wrapper: createQueryWrapper() });
    expect(container.querySelectorAll(".font-eerie").length).toBeGreaterThan(5);

    act(() => useReaderPreferencesStore.setState({ reduceSensoryEffects: true }));

    expect(container.querySelectorAll(".font-eerie")).toHaveLength(0);
    expect(screen.getByText(/hallway0 hallway1/)).toBeInTheDocument();
  });
});
