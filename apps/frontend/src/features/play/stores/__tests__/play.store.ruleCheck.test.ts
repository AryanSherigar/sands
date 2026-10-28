import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlayStore } from "../play.store";
import { PlaythroughData } from "../../types/play.types";
import { SSEHandlers } from "@/shared/lib/sse-client";
import { RuleCheckEventPayload } from "@/shared/types/check.types";

let capturedHandlers: SSEHandlers | null = null;
let capturedBody: Record<string, unknown> | null = null;

vi.mock("@/shared/lib/sse-client", () => ({
  createPostSSEConnection: (
    _url: string,
    body: Record<string, unknown>,
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

const handleSensoryCue = vi.fn();
const handleRuleRevealed = vi.fn();
vi.mock("../../lib/atmosphereSubscriber", () => ({
  handleSensoryCue: (cue: unknown) => handleSensoryCue(cue),
  handleRuleRevealed: (tools: unknown) => handleRuleRevealed(tools),
}));

const ISSUED_AT = 1_760_000_000_000;

const phone: RuleCheckEventPayload = {
  check_id: "chk-1",
  kind: "timed_choice",
  prompt: "The phone rings.",
  options: [
    { id: "answer", label: "Answer it" },
    { id: "ignore", label: "Let it ring" },
  ],
  window_ms: 12000,
  issued_at: ISSUED_AT,
};

function buildPlaythrough(
  overrides: Partial<PlaythroughData> = {},
): PlaythroughData {
  return {
    playthrough_id: "pt-1",
    scenario_id: "sc-1",
    scenario_title: "Night Desk",
    mode: "master",
    creator_name: "Creator",
    enabled_tools: ["rule_checks"],
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
    ...overrides,
  };
}

describe("play.store — rule check handling", () => {
  beforeEach(() => {
    capturedHandlers = null;
    capturedBody = null;
    vi.useRealTimers();
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      pending_rule_check_trigger: null,
      active_rule_check: null,
      is_rule_check_submitting: false,
      last_closed_rule_check_id: null,
      pending_check_trigger: null,
      active_check: null,
      resolved_check_outcome: null,
      streaming_text: "",
      is_narrating: false,
    });
  });

  it("buffers a rule check and only promotes it to the screen when the turn commits", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent("check", JSON.stringify(phone));

    expect(usePlayStore.getState().active_rule_check).toBeNull();
    expect(usePlayStore.getState().pending_rule_check_trigger?.check_id).toBe(
      "chk-1",
    );
    expect(usePlayStore.getState().pending_check_trigger).toBeNull();

    capturedHandlers!.onEvent("done", "");

    expect(usePlayStore.getState().active_rule_check?.check_id).toBe("chk-1");
    expect(usePlayStore.getState().active_rule_check?.initial_remaining_ms).toBe(
      12000,
    );
    expect(usePlayStore.getState().pending_rule_check_trigger).toBeNull();
    expect(usePlayStore.getState().active_check).toBeNull();
  });

  it("starts the countdown from the server clock sent with the prompt", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent(
      "check",
      JSON.stringify({ ...phone, server_time_ms: ISSUED_AT + 4000 }),
    );
    capturedHandlers!.onEvent("done", "");

    expect(usePlayStore.getState().active_rule_check?.initial_remaining_ms).toBe(
      8000,
    );
  });

  it("still routes a dice check to the dice flow", () => {
    usePlayStore.getState().submitTurn("I sneak.");

    capturedHandlers!.onEvent(
      "check",
      JSON.stringify({
        check_id: "dice-1",
        check_type: "stealth",
        difficulty_class: 12,
      }),
    );
    capturedHandlers!.onEvent("done", "");

    expect(usePlayStore.getState().active_check?.check_id).toBe("dice-1");
    expect(usePlayStore.getState().active_rule_check).toBeNull();
  });

  it("blocks free-text turns while a rule check is open", () => {
    usePlayStore.getState().submitTurn("I wait.");
    capturedHandlers!.onEvent("check", JSON.stringify(phone));
    capturedHandlers!.onEvent("done", "");
    capturedHandlers = null;

    usePlayStore.getState().submitTurn("I look around.");

    expect(capturedHandlers).toBeNull();
  });

  it("posts a check_report for the chosen option", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 12000,
        started_at_client_ms: Date.now(),
      },
    });

    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "answer" }, "Answer it");

    expect(capturedBody).toMatchObject({
      action_kind: "check_report",
      check_report: { check_id: "chk-1", choice_id: "answer" },
      playthrough_id: "pt-1",
      participant_id: "participant-1",
    });
    expect(usePlayStore.getState().is_rule_check_submitting).toBe(true);
  });

  it("reports a timeout without a choice", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 0,
        started_at_client_ms: Date.now(),
      },
    });

    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", timed_out: true }, "No answer");

    expect(capturedBody).toMatchObject({
      check_report: { check_id: "chk-1", timed_out: true },
    });
  });

  it("ignores a report for a check that is not the open one", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 12000,
        started_at_client_ms: Date.now(),
      },
    });

    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "other", choice_id: "answer" }, "x");

    expect(capturedBody).toBeNull();
  });

  it("ignores a second report while one is already in flight", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 12000,
        started_at_client_ms: Date.now(),
      },
    });
    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "answer" }, "Answer it");
    capturedBody = null;

    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "ignore" }, "Ignore");

    expect(capturedBody).toBeNull();
  });

  it("closes the prompt when the server confirms it resolved, without a dice outcome", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 12000,
        started_at_client_ms: Date.now(),
      },
    });
    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "answer" }, "Answer it");

    capturedHandlers!.onEvent(
      "check_resolved",
      JSON.stringify({ check_id: "chk-1", kind: "timed_choice" }),
    );

    expect(usePlayStore.getState().active_rule_check).toBeNull();
    expect(usePlayStore.getState().resolved_check_outcome).toBeNull();
  });

  it("opens the next queued prompt when the answering turn commits it", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 12000,
        started_at_client_ms: Date.now(),
      },
    });
    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "answer" }, "Answer it");
    capturedHandlers!.onEvent(
      "check_resolved",
      JSON.stringify({ check_id: "chk-1", kind: "timed_choice" }),
    );
    capturedHandlers!.onEvent(
      "check",
      JSON.stringify({ ...phone, check_id: "chk-2", prompt: "A knock." }),
    );
    capturedHandlers!.onEvent("done", "");

    expect(usePlayStore.getState().active_rule_check?.check_id).toBe("chk-2");
    expect(usePlayStore.getState().is_rule_check_submitting).toBe(false);
  });

  it("clears the submitting flag when the turn degrades", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 12000,
        started_at_client_ms: Date.now(),
      },
    });
    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "answer" }, "Answer it");

    capturedHandlers!.onEvent("degraded", "Couldn't save");

    expect(usePlayStore.getState().is_rule_check_submitting).toBe(false);
  });

  const openAndAnswer = (): void => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 12000,
        started_at_client_ms: Date.now(),
      },
    });
    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "answer" }, "Answer it");
  };

  it("retries a failed answer by sending the same check report again", () => {
    openAndAnswer();
    capturedHandlers!.onEvent(
      "check_resolved",
      JSON.stringify({ check_id: "chk-1", kind: "timed_choice" }),
    );
    capturedHandlers!.onEvent("degraded", "Couldn't save");
    capturedBody = null;

    usePlayStore.getState().retryLastTurn();

    expect(capturedBody).toMatchObject({
      action_kind: "check_report",
      check_report: { check_id: "chk-1", choice_id: "answer" },
    });
  });

  it("retries an answer whose connection dropped before the server confirmed it", () => {
    openAndAnswer();
    capturedHandlers!.onError?.(new Error("network"));
    capturedBody = null;

    usePlayStore.getState().retryLastTurn();

    expect(capturedBody).toMatchObject({
      action_kind: "check_report",
      check_report: { check_id: "chk-1", choice_id: "answer" },
    });
  });

  it("goes back to ordinary retries once the answering turn committed", () => {
    openAndAnswer();
    capturedHandlers!.onEvent("done", "");
    usePlayStore.getState().submitTurn("I look around.");
    capturedHandlers!.onEvent("degraded", "Couldn't save");
    capturedBody = null;

    usePlayStore.getState().retryLastTurn();

    expect(capturedBody).toMatchObject({
      action_kind: "narrative",
      action_text: "I look around.",
    });
  });

  it("resumes an open prompt on load with the time left by the server clock", () => {
    const loaded = buildPlaythrough({
      pending_rule_check: phone,
      server_time_ms: ISSUED_AT + 5000,
    });

    usePlayStore.getState().setPlaythrough(loaded);

    expect(usePlayStore.getState().active_rule_check?.check_id).toBe("chk-1");
    expect(usePlayStore.getState().active_rule_check?.initial_remaining_ms).toBe(
      7000,
    );
  });

  it("resumes with no time left when the window has already passed", () => {
    usePlayStore.getState().setPlaythrough(
      buildPlaythrough({
        pending_rule_check: phone,
        server_time_ms: ISSUED_AT + 90_000,
      }),
    );

    expect(usePlayStore.getState().active_rule_check?.initial_remaining_ms).toBe(
      0,
    );
  });

  it("keeps the running prompt when the same check is reloaded", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 9000,
        started_at_client_ms: 123,
      },
    });

    usePlayStore.getState().setPlaythrough(
      buildPlaythrough({
        pending_rule_check: phone,
        server_time_ms: ISSUED_AT + 100,
      }),
    );

    expect(usePlayStore.getState().active_rule_check?.started_at_client_ms).toBe(
      123,
    );
  });

  it("does not re-arm a prompt that was already answered when a stale refetch arrives", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 9000,
        started_at_client_ms: 123,
      },
    });
    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "answer" }, "Answer it");
    capturedHandlers!.onEvent(
      "check_resolved",
      JSON.stringify({ check_id: "chk-1", kind: "timed_choice" }),
    );

    usePlayStore
      .getState()
      .setPlaythrough(buildPlaythrough({ pending_rule_check: phone }));

    expect(usePlayStore.getState().active_rule_check).toBeNull();
  });

  it("arms a different prompt that the server opens after the answered one", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 9000,
        started_at_client_ms: 123,
      },
    });
    usePlayStore
      .getState()
      .submitCheckReport({ check_id: "chk-1", choice_id: "answer" }, "Answer it");
    capturedHandlers!.onEvent(
      "check_resolved",
      JSON.stringify({ check_id: "chk-1", kind: "timed_choice" }),
    );

    usePlayStore.getState().setPlaythrough(
      buildPlaythrough({ pending_rule_check: { ...phone, check_id: "chk-2" } }),
    );

    expect(usePlayStore.getState().active_rule_check?.check_id).toBe("chk-2");
  });

  it("clears the prompt on load when the server has none open", () => {
    usePlayStore.setState({
      active_rule_check: {
        ...phone,
        initial_remaining_ms: 9000,
        started_at_client_ms: 123,
      },
    });

    usePlayStore.getState().setPlaythrough(buildPlaythrough());

    expect(usePlayStore.getState().active_rule_check).toBeNull();
  });
});


describe("play.store — sensory cue events", () => {
  beforeEach(() => {
    capturedHandlers = null;
    handleSensoryCue.mockClear();
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      streaming_text: "",
      is_narrating: false,
      active_rule_check: null,
      is_rule_check_submitting: false,
      last_check_report: null,
      last_client_action_id: null,
      cue_played_action_id: null,
      cue_played_generation: 0,
    });
  });

  it("hands a cue to the atmosphere subscriber the moment it arrives", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent(
      "sensory_cue",
      JSON.stringify({
        cue: "phone_ring",
        cut_ambient: true,
        silence_duration_ms: 800,
      }),
    );

    expect(handleSensoryCue).toHaveBeenCalledWith({
      cue: "phone_ring",
      cut_ambient: true,
      silence_duration_ms: 800,
    });
  });

  it("ignores a cue the client does not know", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent(
      "sensory_cue",
      JSON.stringify({ cue: "air_horn", cut_ambient: true, silence_duration_ms: 0 }),
    );

    expect(handleSensoryCue).not.toHaveBeenCalled();
  });

  it("does not replay a cue when the same turn is retried after a failed attempt", () => {
    const cue = JSON.stringify({
      cue: "phone_ring",
      cut_ambient: true,
      silence_duration_ms: 800,
    });
    usePlayStore.getState().submitTurn("I wait.");
    capturedHandlers!.onEvent("sensory_cue", cue);

    usePlayStore.getState().retryLastTurn();
    capturedHandlers!.onEvent("sensory_cue", cue);

    expect(handleSensoryCue).toHaveBeenCalledTimes(1);
  });

  it("plays every cue of one attempt, including a second cue", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent(
      "sensory_cue",
      JSON.stringify({ cue: "sudden_silence", cut_ambient: true, silence_duration_ms: 1000 }),
    );
    capturedHandlers!.onEvent(
      "sensory_cue",
      JSON.stringify({ cue: "radio_static", cut_ambient: false, silence_duration_ms: 0 }),
    );

    expect(handleSensoryCue).toHaveBeenCalledTimes(2);
  });

  it("plays the cue on a retry whose first attempt never reached it", () => {
    usePlayStore.getState().submitTurn("I wait.");

    usePlayStore.getState().retryLastTurn();
    capturedHandlers!.onEvent(
      "sensory_cue",
      JSON.stringify({ cue: "phone_ring", cut_ambient: true, silence_duration_ms: 800 }),
    );

    expect(handleSensoryCue).toHaveBeenCalledTimes(1);
  });

  it("plays the cue again for a new action", () => {
    const cue = JSON.stringify({
      cue: "phone_ring",
      cut_ambient: true,
      silence_duration_ms: 800,
    });
    usePlayStore.getState().submitTurn("I wait.");
    capturedHandlers!.onEvent("sensory_cue", cue);
    usePlayStore.setState({ last_client_action_id: null, is_narrating: false });

    usePlayStore.getState().submitTurn("I wait again.");
    capturedHandlers!.onEvent("sensory_cue", cue);

    expect(handleSensoryCue).toHaveBeenCalledTimes(2);
  });

  it("does not treat a cue as the end of the turn", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent(
      "sensory_cue",
      JSON.stringify({
        cue: "phone_ring",
        cut_ambient: true,
        silence_duration_ms: 800,
      }),
    );

    expect(usePlayStore.getState().is_narrating).toBe(true);
  });
});


describe("play.store — state_update events", () => {
  beforeEach(() => {
    capturedHandlers = null;
    usePlayStore.setState({
      playthrough: buildPlaythrough({ state: { clock: 0, sanity: 80 } }),
      streaming_text: "",
      is_narrating: false,
    });
  });

  it("replaces the visible state as soon as it arrives, before narration", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent(
      "state_update",
      JSON.stringify({ state: { clock: 30, sanity: 60 } }),
    );

    expect(usePlayStore.getState().playthrough?.state).toEqual({
      clock: 30,
      sanity: 60,
    });
    expect(usePlayStore.getState().streaming_text).toBe("");
  });

  it("does not end the turn", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent("state_update", JSON.stringify({ state: {} }));

    expect(usePlayStore.getState().is_narrating).toBe(true);
  });

  it("ignores a payload with no state object", () => {
    usePlayStore.getState().submitTurn("I wait.");

    capturedHandlers!.onEvent("state_update", JSON.stringify({ rule_sheet: [] }));

    expect(usePlayStore.getState().playthrough?.state).toEqual({
      clock: 0,
      sanity: 80,
    });
  });

  describe("state_update with a rule sheet", () => {
    const rule = (key: string, status = "intact") => ({
      key,
      number: Number(key.slice(1)),
      text: `Rule ${key}`,
      status,
      source_style: "typed",
    });

    beforeEach(() => {
      handleRuleRevealed.mockClear();
      usePlayStore.getState().submitTurn("I wait.");
    });

    it("replaces the clipboard from the event before narration", () => {
      capturedHandlers!.onEvent(
        "state_update",
        JSON.stringify({ state: { clock: 1 }, rule_sheet: [rule("r1")] }),
      );

      expect(usePlayStore.getState().playthrough?.rule_sheet).toEqual([rule("r1")]);
      expect(usePlayStore.getState().playthrough?.state).toEqual({ clock: 1 });
    });

    it("keeps the clipboard when the event carries no sheet", () => {
      usePlayStore.setState({
        playthrough: buildPlaythrough({ rule_sheet: [rule("r1")] as never }),
      });

      capturedHandlers!.onEvent("state_update", JSON.stringify({ state: {} }));

      expect(usePlayStore.getState().playthrough?.rule_sheet).toHaveLength(1);
    });

    it("rustles once for a newly revealed rule when atmosphere is on", () => {
      usePlayStore.setState({
        playthrough: buildPlaythrough({
          enabled_tools: ["rule_sheet", "atmosphere"],
        }),
      });

      capturedHandlers!.onEvent(
        "state_update",
        JSON.stringify({ state: {}, rule_sheet: [rule("r1")] }),
      );

      expect(handleRuleRevealed).toHaveBeenCalledTimes(1);
      expect(handleRuleRevealed).toHaveBeenCalledWith(["rule_sheet", "atmosphere"]);
    });

    it("does not rustle when an existing rule only changes status", () => {
      usePlayStore.setState({
        playthrough: buildPlaythrough({ rule_sheet: [rule("r1")] as never }),
      });

      capturedHandlers!.onEvent(
        "state_update",
        JSON.stringify({ state: {}, rule_sheet: [rule("r1", "violated")] }),
      );

      expect(handleRuleRevealed).not.toHaveBeenCalled();
    });
  });
});
