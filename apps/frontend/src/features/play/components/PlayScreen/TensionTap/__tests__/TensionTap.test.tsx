import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { emitAlphaEvent } from "@/shared/lib/alpha-events";
import { usePlayStore } from "../../../../stores/play.store";
import type { PlaythroughData } from "../../../../types/play.types";
import { TensionTap } from "../TensionTap";

vi.mock("@/shared/lib/alpha-events", () => ({ emitAlphaEvent: vi.fn() }));

const EVERY_TURNS = ALPHA_CONFIG.tension_prompt_every_turns ?? 15;
const PROMPT = /How tense was that stretch/;

function seedRun(turns: number, extra: Record<string, unknown> = {}): void {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      ended_outcome_tag: null,
      turns: Array.from({ length: turns }, (_, index) => ({ id: `t-${index}` })),
    } as unknown as PlaythroughData,
    is_narrating: false,
    is_check_animation_pending: false,
    active_minigame: null,
    active_check: null,
    active_rule_check: null,
    ...extra,
  });
}

function grow(turns: number): void {
  const current = usePlayStore.getState().playthrough as PlaythroughData;
  usePlayStore.setState({
    playthrough: {
      ...current,
      turns: Array.from({ length: turns }, (_, index) => ({ id: `t-${index}` })),
    } as unknown as PlaythroughData,
  });
}

describe("TensionTap", () => {
  beforeEach(() => vi.mocked(emitAlphaEvent).mockClear());

  it("asks after every N saved turns", async () => {
    seedRun(0);
    render(<TensionTap />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });
    expect(screen.queryByText(PROMPT)).toBeNull();

    grow(EVERY_TURNS - 1);
    expect(screen.queryByText(PROMPT)).toBeNull();
    grow(EVERY_TURNS);

    expect(await screen.findByText(PROMPT)).toBeInTheDocument();
  });

  it("submits a tension_rating event and goes away until the next cadence", async () => {
    seedRun(0);
    const user = userEvent.setup();
    render(<TensionTap />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });
    grow(EVERY_TURNS);

    await user.click(await screen.findByRole("button", { name: "4" }));

    expect(emitAlphaEvent).toHaveBeenCalledWith(
      "tension_rating",
      { turn_number: EVERY_TURNS, rating: 4 },
      { playthroughId: "pt-1" },
    );
    expect(screen.queryByText(PROMPT)).toBeNull();
    grow(EVERY_TURNS + 1);
    expect(screen.queryByText(PROMPT)).toBeNull();
  });

  it.each([
    ["a rule check", { active_rule_check: { check_id: "c1" } }],
    ["a dice check", { active_check: { check_id: "c2" } }],
    ["a minigame", { active_minigame: { minigame_id: "m1" } }],
    ["the narrator speaking", { is_narrating: true }],
  ])("never interrupts %s", async (_label, busyState) => {
    seedRun(0);
    render(<TensionTap />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });
    usePlayStore.setState(busyState as never);

    grow(EVERY_TURNS);

    expect(screen.queryByText(PROMPT)).toBeNull();
  });

  it("never interrupts an ending", () => {
    seedRun(0);
    render(<TensionTap />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });
    usePlayStore.setState({
      playthrough: {
        playthrough_id: "pt-1",
        ended_outcome_tag: "win",
        turns: Array.from({ length: EVERY_TURNS }, (_, i) => ({ id: `t-${i}` })),
      } as unknown as PlaythroughData,
    });

    expect(screen.queryByText(PROMPT)).toBeNull();
  });

  it("does not ask outside alpha mode", () => {
    seedRun(0);
    render(<TensionTap />, { wrapper: createQueryWrapper(NON_ALPHA_CONFIG) });

    grow(EVERY_TURNS);

    expect(screen.queryByText(PROMPT)).toBeNull();
  });
});
