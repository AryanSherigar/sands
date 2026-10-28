import { describe, it, expect, vi, beforeEach } from "vitest";
import { usePlayStore } from "../play.store";
import { PlaythroughData } from "../../types/play.types";
import { SSEHandlers } from "@/shared/lib/sse-client";
import {
  DEFAULT_COMPOSURE_CONFIG,
  MinigameEventPayload,
} from "@/shared/types/minigame.types";
import { queryClient } from "@/shared/lib/query-client";
import { getPlaythrough } from "@/shared/api/playthroughs.api";
import {
  ALPHA_PAUSED_MESSAGE,
  AlphaPausedError,
} from "@/shared/lib/alpha-paused-error";
import { RateLimitError } from "@/shared/lib/rate-limit-error";
import { selectCanRetryTurn } from "../play.selectors";

let capturedHandlers: SSEHandlers | null = null;
let capturedBody: unknown = null;

vi.mock("@/shared/lib/sse-client", () => ({
  createPostSSEConnection: (
    _url: string,
    body: unknown,
    _token: string | null,
    handlers: SSEHandlers,
  ) => {
    capturedHandlers = handlers;
    capturedBody = body;
    return vi.fn();
  },
}));

vi.mock("@/shared/api/playthroughs.api", () => ({
  getPlaythrough: vi.fn(),
}));

function buildPlaythrough(): PlaythroughData {
  return {
    playthrough_id: "pt-1",
    scenario_id: "sc-1",
    scenario_title: "The Hollow Cairn",
    mode: "master",
    creator_name: "Creator",
    enabled_tools: [],
    opening_premise: "Begin.",
    world_lore: "",
    key_facts: [],
    story_cards: [],
    character_name: "Adventurer",
    custom_fields: [],
    turns: [],
    is_spectator: false,
    participant_id: "participant-1",
    can_act: true,
    next_actor_label: null,
    entities: [],
    active_conditions: [],
    objectives: [],
    player_stats: [],
    player_inventory: [],
    pending_minigame: null,
    pending_check: null,
    pending_rule_check: null,
    server_time_ms: null,
    state: {},
    hud_hints: { meters: [] },
    rule_sheet: [],
    ended_outcome_tag: null,
    ended_outcome_title: null,
    ended_outcome_text: null,
    action_chips: [],
  };
}

describe("play.store — turn_summary handling", () => {
  beforeEach(() => {
    capturedHandlers = null;
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      pending_chapter_delta: null,
      streaming_text: "",
      is_narrating: false,
    });
  });

  it("commits the turn with the server's turn id from done", () => {
    usePlayStore.getState().submitTurn("I sign the Log.");
    capturedHandlers!.onEvent("narration", "The pen is cold.");
    capturedHandlers!.onEvent(
      "done",
      JSON.stringify({ turn_id: "turn-uuid-1" }),
    );
    expect(usePlayStore.getState().playthrough?.turns[0].id).toBe("turn-uuid-1");
  });

  it("keeps a local id when done has no turn id", () => {
    usePlayStore.getState().submitTurn("I wait.");
    capturedHandlers!.onEvent("narration", "Nothing moves.");
    capturedHandlers!.onEvent("done", "");
    expect(usePlayStore.getState().playthrough?.turns[0].id).toMatch(/^local-/);
  });

  it("holds the delta on turn_summary and only attaches it to the committed turn on done", () => {
    usePlayStore.getState().submitTurn("I strike the warden.");
    expect(capturedHandlers).not.toBeNull();

    capturedHandlers!.onEvent(
      "narration",
      "The blade connects with a dull thud.",
    );
    // Not yet committed — the summary strip must not appear mid-stream.
    expect(usePlayStore.getState().playthrough?.turns).toHaveLength(0);

    capturedHandlers!.onEvent(
      "turn_summary",
      JSON.stringify({
        stat_changes: [
          {
            path: "player.health",
            label: "Health",
            before: 100,
            after: 85,
            delta: -15,
          },
        ],
        inventory_changes: [],
        active_conditions: ["Bleeding Out"],
      }),
    );

    // active_conditions is live, applied immediately.
    expect(usePlayStore.getState().playthrough?.active_conditions).toEqual([
      "Bleeding Out",
    ]);
    // The delta is held, not yet on any committed turn.
    expect(usePlayStore.getState().pending_chapter_delta).not.toBeNull();
    expect(usePlayStore.getState().playthrough?.turns).toHaveLength(0);

    capturedHandlers!.onEvent("done", "");

    const turns = usePlayStore.getState().playthrough?.turns ?? [];
    expect(turns).toHaveLength(1);
    expect(turns[0].chapter_delta?.stat_changes[0].label).toBe("Health");
    expect(usePlayStore.getState().pending_chapter_delta).toBeNull();
  });
});

describe("play.store — minigame trigger/result handling", () => {
  beforeEach(() => {
    capturedHandlers = null;
    capturedBody = null;
    vi.mocked(getPlaythrough).mockReset();
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      pending_minigame_trigger: null,
      active_minigame: null,
      pending_minigame_result: null,
      active_check: null,
      streaming_text: "",
      is_narrating: false,
    });
  });

  const minigamePayload: MinigameEventPayload = {
    minigame_id: "mg-1",
    minigame_type: "dodge",
    label: "Rune Puzzle",
    dodge_config: { difficulty: 3 },
    timeout_seconds: 20,
  };

  it("buffers a minigame event and only promotes it to active_minigame on done", () => {
    usePlayStore.getState().submitTurn("I open the door.");
    expect(capturedHandlers).not.toBeNull();

    capturedHandlers!.onEvent("minigame", JSON.stringify(minigamePayload));

    // Buffered only — the overlay must not appear mid-stream.
    expect(usePlayStore.getState().active_minigame).toBeNull();
    expect(usePlayStore.getState().pending_minigame_trigger).toEqual(
      minigamePayload,
    );

    capturedHandlers!.onEvent("done", "");

    expect(usePlayStore.getState().active_minigame).toEqual(minigamePayload);
    expect(usePlayStore.getState().pending_minigame_trigger).toBeNull();
  });

  it("submitMinigameResult posts action_kind minigame_result with the given payload", () => {
    usePlayStore.setState({ active_minigame: minigamePayload });
    usePlayStore.getState().submitMinigameResult({
      minigame_id: "mg-1",
      outcome_tag: "win",
      score: 10,
    });

    expect(capturedHandlers).not.toBeNull();
    expect(capturedBody).toMatchObject({
      action_kind: "minigame_result",
      minigame_result: { minigame_id: "mg-1", outcome_tag: "win", score: 10 },
    });
  });

  it("retains a failed result, reuses its attempt id, and ignores duplicate completion", async () => {
    usePlayStore.setState({
      active_minigame: { ...minigamePayload, attempt_id: "attempt-1" },
    });
    usePlayStore.getState().submitMinigameResult({
      minigame_id: "mg-1",
      outcome_tag: "win",
    });
    usePlayStore.getState().submitMinigameResult({
      minigame_id: "mg-1",
      outcome_tag: "win",
    });

    expect(capturedBody).toMatchObject({
      minigame_result: { attempt_id: "attempt-1" },
    });
    capturedHandlers?.onError?.(new Error("submission failed"));
    expect(usePlayStore.getState().pending_minigame_result).toMatchObject({
      status: "retryable",
      attempts: 1,
    });

    vi.mocked(getPlaythrough).mockResolvedValue({
      state: {
        _pending_minigame: { ...minigamePayload, attempt_id: "attempt-1" },
      },
    } as never);
    await usePlayStore.getState().retryMinigameResult();
    expect(usePlayStore.getState().pending_minigame_result).toMatchObject({
      status: "submitting",
      attempts: 2,
      result: { attempt_id: "attempt-1" },
    });
  });

  it("reconciles a committed attempt before retrying instead of posting it again", async () => {
    usePlayStore.setState({
      active_minigame: { ...minigamePayload, attempt_id: "attempt-1" },
    });
    usePlayStore.getState().submitMinigameResult({
      minigame_id: "mg-1",
      outcome_tag: "win",
    });
    capturedHandlers?.onError?.(new Error("submission failed"));
    const firstPost = capturedBody;

    vi.mocked(getPlaythrough).mockResolvedValue({ state: {} } as never);
    await usePlayStore.getState().retryMinigameResult();

    expect(capturedBody).toBe(firstPost);
    expect(usePlayStore.getState().active_minigame).toBeNull();
    expect(usePlayStore.getState().pending_minigame_result).toBeNull();
  });

  it("does not submit a timeout fallback after the original attempt committed", async () => {
    usePlayStore.setState({
      active_minigame: { ...minigamePayload, attempt_id: "attempt-1" },
      pending_minigame_result: {
        result: {
          minigame_id: "mg-1",
          attempt_id: "attempt-1",
          outcome_tag: "win",
        },
        action_text: "You finish.",
        client_action_id: "action-original",
        attempts: 3,
        status: "terminal",
        fallback_used: false,
      },
    });

    vi.mocked(getPlaythrough).mockResolvedValue({ state: {} } as never);
    await usePlayStore.getState().submitMinigameTimeoutFallback();

    expect(capturedBody).toBeNull();
    expect(usePlayStore.getState().active_minigame).toBeNull();
    expect(usePlayStore.getState().pending_minigame_result).toBeNull();
  });

  it("clearActiveMinigame nulls active_minigame immediately", () => {
    usePlayStore.setState({ active_minigame: minigamePayload });
    usePlayStore.getState().clearActiveMinigame();
    expect(usePlayStore.getState().active_minigame).toBeNull();
  });

  it("updates and clears reader_font_override", () => {
    usePlayStore.getState().setReaderFontOverride("special-elite");
    expect(usePlayStore.getState().reader_font_override).toBe("special-elite");

    usePlayStore.getState().setReaderFontOverride(null);
    expect(usePlayStore.getState().reader_font_override).toBeNull();
  });
});

describe("play.store — check proposal/resolution handling", () => {
  beforeEach(() => {
    capturedHandlers = null;
    capturedBody = null;
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      pending_check_trigger: null,
      active_check: null,
      is_narrating: false,
      is_check_animation_pending: false,
      buffered_check_narration: "",
      check_terminal_pending: null,
      resolved_check_outcome: null,
      streaming_text: "",
    });
  });

  const checkPayload = {
    check_id: "check-1",
    check_type: "lockpicking",
    difficulty_class: 15,
    reasoning: "The mechanism is old and delicate.",
  };

  it("buffers a check event and only promotes it to active_check on done", () => {
    usePlayStore.getState().submitTurn("I try the lock.");
    expect(capturedHandlers).not.toBeNull();

    capturedHandlers!.onEvent("check", JSON.stringify(checkPayload));

    // Buffered only — the prompt must not appear mid-stream.
    expect(usePlayStore.getState().active_check).toBeNull();
    expect(usePlayStore.getState().pending_check_trigger).toEqual({
      ...checkPayload,
      resolved_roll: null,
    });

    capturedHandlers!.onEvent("done", "");

    expect(usePlayStore.getState().active_check).toEqual({
      ...checkPayload,
      resolved_roll: null,
    });
    expect(usePlayStore.getState().pending_check_trigger).toBeNull();
  });

  it("submitCheckResolution posts action_kind check_resolution with the given payload", () => {
    usePlayStore.setState({
      active_check: { ...checkPayload, resolved_roll: null },
    });
    usePlayStore.getState().submitCheckResolution({
      check_id: "check-1",
      resolution: "attempt",
    });

    expect(capturedBody).toMatchObject({
      action_kind: "check_resolution",
      check_resolution: { check_id: "check-1", resolution: "attempt" },
    });
  });

  it("buffers narration during the roll animation and reveals it on revealCheckAnimation", () => {
    usePlayStore.setState({
      active_check: { ...checkPayload, resolved_roll: null },
    });
    usePlayStore.getState().submitCheckResolution({
      check_id: "check-1",
      resolution: "attempt",
    });
    expect(usePlayStore.getState().is_check_animation_pending).toBe(true);

    capturedHandlers!.onEvent(
      "check_resolved",
      JSON.stringify({
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        resolved_roll: 17,
        is_success: true,
      }),
    );
    capturedHandlers!.onEvent("narration", "Your fingers find the tumblers.");

    // Buffered, not yet visible — the animation is still "running".
    expect(usePlayStore.getState().streaming_text).toBe("");
    expect(usePlayStore.getState().buffered_check_narration).toBe(
      "Your fingers find the tumblers.",
    );
    expect(usePlayStore.getState().resolved_check_outcome?.resolved_roll).toBe(
      17,
    );

    usePlayStore.getState().revealCheckAnimation();

    expect(usePlayStore.getState().is_check_animation_pending).toBe(false);
    expect(usePlayStore.getState().streaming_text).toBe(
      "Your fingers find the tumblers.",
    );
    expect(usePlayStore.getState().buffered_check_narration).toBe("");
  });

  it("defers the done event until the animation is revealed, then commits", () => {
    usePlayStore.setState({
      active_check: { ...checkPayload, resolved_roll: null },
    });
    usePlayStore.getState().submitCheckResolution({
      check_id: "check-1",
      resolution: "attempt",
    });

    capturedHandlers!.onEvent("narration", "Your fingers find the tumblers.");
    capturedHandlers!.onEvent("done", "");

    // The stream already finished, but the turn must not commit yet.
    expect(usePlayStore.getState().is_narrating).toBe(true);
    expect(usePlayStore.getState().playthrough?.turns).toHaveLength(0);

    usePlayStore.getState().revealCheckAnimation();

    expect(usePlayStore.getState().is_narrating).toBe(false);
    const turns = usePlayStore.getState().playthrough?.turns ?? [];
    expect(turns).toHaveLength(1);
    expect(turns[0].narration_text).toBe("Your fingers find the tumblers.");
  });

  it("defers a degraded event until the animation is revealed", () => {
    usePlayStore.setState({
      active_check: { ...checkPayload, resolved_roll: null },
    });
    usePlayStore.getState().submitCheckResolution({
      check_id: "check-1",
      resolution: "attempt",
    });

    capturedHandlers!.onEvent("degraded", "Your turn couldn't be saved.");

    // Still animating — the error must not surface yet.
    expect(usePlayStore.getState().degraded_message).toBeNull();
    expect(usePlayStore.getState().is_narrating).toBe(true);

    usePlayStore.getState().revealCheckAnimation();

    expect(usePlayStore.getState().degraded_message).toBe(
      "Your turn couldn't be saved.",
    );
    expect(usePlayStore.getState().is_narrating).toBe(false);
  });

  it("streams a declined check's narration immediately, with no animation", () => {
    usePlayStore.setState({
      active_check: { ...checkPayload, resolved_roll: null },
    });
    usePlayStore.getState().submitCheckResolution({
      check_id: "check-1",
      resolution: "decline",
    });

    expect(usePlayStore.getState().is_check_animation_pending).toBe(false);
    capturedHandlers!.onEvent("narration", "You step back from the lock.");

    expect(usePlayStore.getState().streaming_text).toBe(
      "You step back from the lock.",
    );
  });
});

describe("play.store — playthrough_ended handling", () => {
  beforeEach(() => {
    capturedHandlers = null;
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      pending_playthrough_ended: null,
      streaming_text: "",
      is_narrating: false,
      active_minigame: null,
      active_check: null,
    });
  });

  const endedPayload = {
    outcome_tag: "win" as const,
    outcome_title: "The Ashen Ending",
    outcome_text: "The Warden kneels.",
  };

  it("buffers playthrough_ended and only applies it to the committed playthrough on done", () => {
    usePlayStore.getState().submitTurn("I strike the killing blow.");
    expect(capturedHandlers).not.toBeNull();

    capturedHandlers!.onEvent(
      "playthrough_ended",
      JSON.stringify(endedPayload),
    );

    // Buffered only — the ending must not apply mid-stream.
    expect(usePlayStore.getState().playthrough?.ended_outcome_tag).toBeNull();
    expect(usePlayStore.getState().pending_playthrough_ended).toEqual(
      endedPayload,
    );

    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    capturedHandlers!.onEvent("done", "");

    const playthrough = usePlayStore.getState().playthrough;
    expect(playthrough?.ended_outcome_tag).toBe("win");
    expect(playthrough?.ended_outcome_title).toBe("The Ashen Ending");
    expect(playthrough?.ended_outcome_text).toBe("The Warden kneels.");
    expect(usePlayStore.getState().pending_playthrough_ended).toBeNull();
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["playthrough", "pt-1"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["playthrough-turns", "pt-1"],
    });

    invalidateSpy.mockRestore();
  });

  it("also invalidates the playthrough query on an ordinary turn with no ending", () => {
    // Guards against HIGH-01: PlayPage rebuilds its store snapshot from
    // serverPlaythrough + turnsData on every change, so leaving
    // ["playthrough", id] stale on a normal turn reverts locally-applied
    // fields (e.g. active_conditions) back to the pre-turn server state.
    usePlayStore.getState().submitTurn("I look around.");
    expect(capturedHandlers).not.toBeNull();

    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    capturedHandlers!.onEvent("done", "");

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["playthrough", "pt-1"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["playthrough-turns", "pt-1"],
    });
    expect(usePlayStore.getState().playthrough?.ended_outcome_tag).toBeNull();

    invalidateSpy.mockRestore();
  });

  it("blocks further submission once the playthrough has ended", () => {
    usePlayStore.setState({
      playthrough: {
        ...buildPlaythrough(),
        ended_outcome_tag: "win",
        ended_outcome_title: "The Ashen Ending",
        ended_outcome_text: "The Warden kneels.",
      },
    });

    usePlayStore.getState().submitTurn("One more action.");
    expect(capturedHandlers).toBeNull();

    usePlayStore.getState().continueTurn();
    expect(capturedHandlers).toBeNull();
  });
});

describe("play.store — narration_audio handling", () => {
  beforeEach(() => {
    capturedHandlers = null;
    capturedBody = null;
    queryClient.removeQueries({ queryKey: ["voice-output-preference"] });
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      pending_audio_url: null,
      streaming_text: "",
      is_narrating: false,
      active_minigame: null,
      active_check: null,
    });
  });

  it("defaults voice_output_requested to false when the preference hasn't loaded", () => {
    usePlayStore.getState().submitTurn("I strike the warden.");

    expect((capturedBody as { voice_output_requested: boolean })
      .voice_output_requested).toBe(false);
  });

  it("sends voice_output_requested true once the preference is cached enabled", () => {
    queryClient.setQueryData(["voice-output-preference"], {
      voice_output_enabled: true,
    });

    usePlayStore.getState().submitTurn("I strike the warden.");

    expect((capturedBody as { voice_output_requested: boolean })
      .voice_output_requested).toBe(true);
  });

  it("holds the audio url on narration_audio and only attaches it to the committed turn on done", () => {
    usePlayStore.getState().submitTurn("I strike the warden.");
    expect(capturedHandlers).not.toBeNull();

    capturedHandlers!.onEvent("narration", "The blade connects.");
    capturedHandlers!.onEvent(
      "narration_audio",
      "https://storage.googleapis.com/fake-bucket/narration-audio/1.wav",
    );

    // Not yet committed — mid-stream.
    expect(usePlayStore.getState().playthrough?.turns).toHaveLength(0);
    expect(usePlayStore.getState().pending_audio_url).toBe(
      "https://storage.googleapis.com/fake-bucket/narration-audio/1.wav",
    );

    capturedHandlers!.onEvent("done", "");

    const turns = usePlayStore.getState().playthrough?.turns ?? [];
    expect(turns).toHaveLength(1);
    expect(turns[0].audio_url).toBe(
      "https://storage.googleapis.com/fake-bucket/narration-audio/1.wav",
    );
    expect(usePlayStore.getState().pending_audio_url).toBeNull();
  });

  it("clears pending_audio_url when the stream is stopped", () => {
    usePlayStore.getState().submitTurn("I strike the warden.");
    capturedHandlers!.onEvent(
      "narration_audio",
      "https://storage.googleapis.com/fake-bucket/narration-audio/1.wav",
    );
    expect(usePlayStore.getState().pending_audio_url).not.toBeNull();

    usePlayStore.getState().stopGeneration();

    expect(usePlayStore.getState().pending_audio_url).toBeNull();
  });
});

describe("play.store — rate limits and quota notices", () => {
  beforeEach(() => {
    capturedHandlers = null;
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      streaming_text: "",
      is_narrating: false,
      degraded_message: null,
      quota_notice_message: null,
    });
  });

  it("shows the server's limit message when the turn is refused", () => {
    usePlayStore.getState().submitTurn("I open the door.");

    capturedHandlers!.onError?.(
      new RateLimitError(
        {
          detail: "You've reached today's turn limit. It resets at 00:00 UTC.",
          code: "quota_exceeded",
          scope: "turn",
          reset_at: "2026-10-27T00:00:00Z",
        },
        3600,
      ),
    );

    const state = usePlayStore.getState();
    expect(state.is_narrating).toBe(false);
    expect(state.degraded_message).toBe(
      "You've reached today's turn limit. It resets at 00:00 UTC.",
    );
  });

  it("shows the calm closed message and hides retry when turns are paused", () => {
    usePlayStore.getState().submitTurn("I open the door.");

    capturedHandlers!.onError?.(new AlphaPausedError());

    const state = usePlayStore.getState();
    expect(state.is_narrating).toBe(false);
    expect(state.degraded_message).toBe(ALPHA_PAUSED_MESSAGE);
    expect(state.is_turn_paused).toBe(true);
    expect(selectCanRetryTurn(state)).toBe(false);
  });

  it("clears the paused state when the next turn is submitted", () => {
    usePlayStore.setState({ is_turn_paused: true });

    usePlayStore.getState().submitTurn("I try again.");

    expect(usePlayStore.getState().is_turn_paused).toBe(false);
  });

  it("keeps the generic message for an ordinary connection failure", () => {
    usePlayStore.getState().submitTurn("I open the door.");

    capturedHandlers!.onError?.(new Error("network down"));

    expect(usePlayStore.getState().degraded_message).toMatch(/Connection lost/);
  });

  it("records a quota notice and still commits the turn on done", () => {
    usePlayStore.getState().submitTurn("I look around.");

    capturedHandlers!.onEvent("narration", "A dim hall.");
    capturedHandlers!.onEvent(
      "quota_notice",
      JSON.stringify({
        feature: "scene_image",
        code: "quota_exceeded",
        detail: "You've reached today's scene image limit.",
        reset_at: "2026-10-27T00:00:00Z",
      }),
    );
    capturedHandlers!.onEvent("done", "");

    const state = usePlayStore.getState();
    expect(state.quota_notice_message).toBe(
      "You've reached today's scene image limit.",
    );
    expect(state.playthrough?.turns).toHaveLength(1);
  });

  it("clears a stale quota notice when the next turn starts", () => {
    usePlayStore.setState({ quota_notice_message: "old notice" });

    usePlayStore.getState().submitTurn("I wait.");

    expect(usePlayStore.getState().quota_notice_message).toBeNull();
  });
});

describe("play.store — input truncation notice", () => {
  beforeEach(() => {
    capturedHandlers = null;
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      streaming_text: "",
      is_narrating: false,
      input_truncated_message: null,
    });
  });

  it("records a notice from the input_truncated event and still commits the turn", () => {
    usePlayStore.getState().submitTurn("I search everything.");

    capturedHandlers!.onEvent(
      "input_truncated",
      JSON.stringify({ original_length: 3000, max_length: 2000 }),
    );
    capturedHandlers!.onEvent("narration", "The room is bare.");
    capturedHandlers!.onEvent("done", "");

    const state = usePlayStore.getState();
    expect(state.input_truncated_message).toMatch(/first 2000 characters/);
    expect(state.playthrough?.turns).toHaveLength(1);
  });

  it("clears a stale notice when the next turn starts", () => {
    usePlayStore.setState({ input_truncated_message: "old notice" });

    usePlayStore.getState().submitTurn("I wait.");

    expect(usePlayStore.getState().input_truncated_message).toBeNull();
  });

  it("clears the notice on dismissal", () => {
    usePlayStore.setState({ input_truncated_message: "cut" });

    usePlayStore.getState().clearInputTruncatedMessage();

    expect(usePlayStore.getState().input_truncated_message).toBeNull();
  });
});

describe("play.store — client_action_id", () => {
  const UUID_PATTERN =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

  const minigamePayload: MinigameEventPayload = {
    minigame_id: "mg-1",
    minigame_type: "dodge",
    label: "Rune Puzzle",
    dodge_config: { difficulty: 3 },
    timeout_seconds: 20,
    attempt_id: "attempt-1",
  };

  function sentActionId(): string {
    return (capturedBody as { client_action_id: string }).client_action_id;
  }

  beforeEach(() => {
    capturedHandlers = null;
    capturedBody = null;
    vi.mocked(getPlaythrough).mockReset();
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      active_minigame: null,
      pending_minigame_result: null,
      active_check: null,
      last_submitted_action: "",
      last_client_action_id: null,
      streaming_text: "",
      is_narrating: false,
    });
  });

  it("sends a UUID client_action_id with a narrative action", () => {
    usePlayStore.getState().submitTurn("I open the door.");

    expect(sentActionId()).toMatch(UUID_PATTERN);
  });

  it("generates a new id for every new submission", () => {
    usePlayStore.getState().submitTurn("I open the door.");
    const first = sentActionId();
    capturedHandlers!.onEvent("done", "");

    usePlayStore.getState().submitTurn("I open the door.");

    expect(sentActionId()).not.toBe(first);
  });

  it("reuses the id when retrying a turn that did not finish", () => {
    usePlayStore.getState().submitTurn("I open the door.");
    const first = sentActionId();
    capturedHandlers!.onError?.(new Error("connection lost"));

    usePlayStore.getState().retryLastTurn();

    expect(capturedBody).toMatchObject({ action_text: "I open the door." });
    expect(sentActionId()).toBe(first);
  });

  it("does not resubmit once the last turn already saved", () => {
    usePlayStore.getState().submitTurn("I open the door.");
    capturedHandlers!.onEvent("done", "");
    expect(usePlayStore.getState().last_client_action_id).toBeNull();
    capturedBody = null;

    usePlayStore.getState().retryLastTurn();

    expect(capturedBody).toBeNull();
  });

  it("uses a new id for a new action after stopping a stream", () => {
    usePlayStore.getState().submitTurn("I open the door.");
    const first = sentActionId();
    usePlayStore.getState().stopGeneration();

    usePlayStore.getState().submitTurn("I open the door.");

    expect(sentActionId()).not.toBe(first);
  });

  it("sends a fresh id for each check resolution", () => {
    usePlayStore.setState({
      active_check: {
        check_id: "check-1",
        check_type: "lockpicking",
        difficulty_class: 15,
        reasoning: "Delicate.",
      } as never,
    });

    usePlayStore
      .getState()
      .submitCheckResolution({ check_id: "check-1", resolution: "decline" });

    expect(sentActionId()).toMatch(UUID_PATTERN);
  });

  it("reuses a minigame result's id on retry and mints a new one for the timeout fallback", async () => {
    usePlayStore.setState({ active_minigame: minigamePayload });
    usePlayStore.getState().submitMinigameResult({
      minigame_id: "mg-1",
      outcome_tag: "win",
    });
    const original = sentActionId();
    expect(original).toMatch(UUID_PATTERN);
    capturedHandlers?.onError?.(new Error("submission failed"));

    vi.mocked(getPlaythrough).mockResolvedValue({
      state: { _pending_minigame: minigamePayload },
    } as never);
    await usePlayStore.getState().retryMinigameResult();
    expect(sentActionId()).toBe(original);

    usePlayStore.setState({
      pending_minigame_result: {
        ...usePlayStore.getState().pending_minigame_result!,
        status: "terminal",
      },
    });
    await usePlayStore.getState().submitMinigameTimeoutFallback();

    expect(capturedBody).toMatchObject({
      minigame_result: { outcome_tag: "timeout" },
    });
    expect(sentActionId()).not.toBe(original);
    expect(sentActionId()).toMatch(UUID_PATTERN);
  });
});

describe("play.store — memory_degraded handling", () => {
  beforeEach(() => {
    capturedHandlers = null;
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      active_minigame: null,
      active_check: null,
      memory_degraded_reasons: [],
      streaming_text: "",
      is_narrating: false,
    });
  });

  it("records the reasons from a memory_degraded event without ending the turn", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent(
      "memory_degraded",
      JSON.stringify({ reasons: ["extraction_failed", "delivery_lag"] }),
    );

    expect(usePlayStore.getState().memory_degraded_reasons).toEqual([
      "extraction_failed",
      "delivery_lag",
    ]);
    expect(usePlayStore.getState().is_narrating).toBe(true);
  });

  it("keeps the reasons through done when the same turn reported them", () => {
    usePlayStore.getState().submitTurn("I wait.");
    capturedHandlers!.onEvent("narration", "Nothing happens.");

    capturedHandlers!.onEvent(
      "memory_degraded",
      JSON.stringify({ reasons: ["indexing_lag"] }),
    );
    capturedHandlers!.onEvent("done", "");

    expect(usePlayStore.getState().memory_degraded_reasons).toEqual([
      "indexing_lag",
    ]);
  });

  it("clears the reasons when a turn finishes without the event", () => {
    usePlayStore.setState({ memory_degraded_reasons: ["extraction_failed"] });
    usePlayStore.getState().submitTurn("I wait.");
    capturedHandlers!.onEvent("narration", "Nothing happens.");

    capturedHandlers!.onEvent("done", "");

    expect(usePlayStore.getState().memory_degraded_reasons).toEqual([]);
  });

  it("keeps the reasons when the turn degrades instead of finishing", () => {
    usePlayStore.setState({ memory_degraded_reasons: ["extraction_failed"] });
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent("degraded", "Your turn couldn't be saved.");

    expect(usePlayStore.getState().memory_degraded_reasons).toEqual([
      "extraction_failed",
    ]);
  });
});

describe("play.store — minigame action text and client effects", () => {
  const TAKEOVER = {
    kind: "input_takeover",
    params: { text: "Get me out of here, Orr", lock_ms: 4500, type_ms_per_char: 60 },
  };

  beforeEach(() => {
    capturedHandlers = null;
    capturedBody = null;
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      pending_minigame_result: null,
      active_minigame: null,
      active_check: null,
      effects_action_id: null,
      pending_client_effects: [],
      active_client_effect: null,
      queued_client_effects: [],
      streaming_text: "",
      is_narrating: false,
    });
  });

  it("sends the minigame's own result line as the action", () => {
    usePlayStore.setState({
      active_minigame: {
        minigame_id: "mg-hum",
        minigame_type: "rhythm_composure",
        label: "The Hum",
        timeout_seconds: 30,
        composure_config: {
          ...DEFAULT_COMPOSURE_CONFIG,
          texts: { ...DEFAULT_COMPOSURE_CONFIG.texts, win_text: "You hum until the chime." },
        },
      },
    });
    usePlayStore.getState().submitMinigameResult({ minigame_id: "mg-hum", outcome_tag: "win" });
    expect((capturedBody as { action_text: string }).action_text).toBe(
      "You hum until the chime.",
    );
  });

  it("holds a client effect until the turn commits", () => {
    usePlayStore.getState().submitTurn("I read the tally.");
    capturedHandlers!.onEvent("client_effect", JSON.stringify(TAKEOVER));
    expect(usePlayStore.getState().active_client_effect).toBeNull();
    capturedHandlers!.onEvent("narration", "The numbers do not match.");
    capturedHandlers!.onEvent("done", "");
    expect(usePlayStore.getState().active_client_effect).toEqual(TAKEOVER);
  });

  it("does not queue an effect twice for a retry", () => {
    usePlayStore.getState().submitTurn("I read the tally.");
    const body = capturedBody as Parameters<
      ReturnType<typeof usePlayStore.getState>["_startTurnStream"]
    >[0];
    capturedHandlers!.onEvent("client_effect", JSON.stringify(TAKEOVER));
    usePlayStore.getState()._startTurnStream(body, "I read the tally.");
    capturedHandlers!.onEvent("client_effect", JSON.stringify(TAKEOVER));
    capturedHandlers!.onEvent("narration", "The numbers do not match.");
    capturedHandlers!.onEvent("done", "");
    expect(usePlayStore.getState().active_client_effect).toEqual(TAKEOVER);
    expect(usePlayStore.getState().queued_client_effects).toEqual([]);
  });

  it("plays queued effects one after another", () => {
    usePlayStore.getState().submitTurn("I pick up.");
    const echo = { kind: "phone_echo", params: { record_ms: 6000, delay_ms: 2500 } };
    capturedHandlers!.onEvent("client_effect", JSON.stringify(TAKEOVER));
    capturedHandlers!.onEvent("client_effect", JSON.stringify(echo));
    capturedHandlers!.onEvent("done", "");
    expect(usePlayStore.getState().active_client_effect).toEqual(TAKEOVER);
    usePlayStore.getState().finishClientEffect();
    expect(usePlayStore.getState().active_client_effect).toEqual(echo);
    usePlayStore.getState().finishClientEffect();
    expect(usePlayStore.getState().active_client_effect).toBeNull();
  });
});
