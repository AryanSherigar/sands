import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlayStore } from "../play.store";
import { PlaythroughData } from "../../types/play.types";
import { SSEHandlers } from "@/shared/lib/sse-client";
import trace from "../../__fixtures__/night_desk_sse_trace.json";

// The trace is a full night recorded by apps/turn-resolution-service/scripts/
// night_desk_e2e.py (the violator run: phone echo, takeover, poster, Hum). Each turn is replayed through the real
// store, event by event, and the store must end each turn in the shape the
// events describe.

interface TraceEvent {
  event: string;
  data: unknown;
}
interface TraceTurn {
  request: Record<string, unknown>;
  events: TraceEvent[];
}

const turns = trace as unknown as TraceTurn[];
const HIDDEN_ROOTS = [
  "seed",
  "count",
  "check",
  "fragments",
  "visit",
  "flags",
  "events",
  "visited",
  "cabin",
  "rule_status",
];
const REVEALED_RULE_COUNT = 7;
const NIGHT_TURNS = 21;

let capturedHandlers: SSEHandlers | null = null;

vi.mock("@/shared/lib/sse-client", () => ({
  createPostSSEConnection: (
    _url: string,
    _body: Record<string, unknown>,
    _token: string | null,
    handlers: SSEHandlers,
  ) => {
    capturedHandlers = handlers;
    return vi.fn();
  },
}));

vi.mock("@/shared/api/playthroughs.api", () => ({ getPlaythrough: vi.fn() }));

const playedCues: string[] = [];
vi.mock("../../lib/atmosphereSubscriber", () => ({
  handleSensoryCue: (cue: { cue: string }) => playedCues.push(cue.cue),
  handleRuleRevealed: vi.fn(),
}));

function buildPlaythrough(): PlaythroughData {
  const first = turns[0].request;
  return {
    playthrough_id: String(first.playthrough_id),
    scenario_id: "night-desk",
    scenario_title: "Night Desk, Floor 9",
    mode: "master",
    creator_name: "Creator",
    enabled_tools: [
      "rule_checks",
      "rule_sheet",
      "status_hud",
      "atmosphere",
      "composure",
    ],
    opening_premise: "",
    world_lore: "",
    key_facts: [],
    story_cards: [],
    character_name: "Alex",
    custom_fields: [],
    turns: [],
    is_spectator: false,
    participant_id: String(first.participant_id),
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

const asText = (data: unknown): string =>
  typeof data === "string" ? data : JSON.stringify(data);

const eventsNamed = (turn: TraceTurn, name: string): TraceEvent[] =>
  turn.events.filter((item) => item.event === name);

function replay(turn: TraceTurn): void {
  usePlayStore.getState()._startTurnStream(
    {
      action_kind: "narrative",
      action_mode: "do",
      voice_output_requested: false,
      ...turn.request,
    } as unknown as Parameters<
      ReturnType<typeof usePlayStore.getState>["_startTurnStream"]
    >[0],
    String(turn.request.action_text),
  );
  for (const item of turn.events) {
    capturedHandlers!.onEvent(item.event, asText(item.data));
  }
}

describe("play.store replaying a recorded Night Desk night", () => {
  beforeEach(() => {
    capturedHandlers = null;
    playedCues.length = 0;
    usePlayStore.setState({
      playthrough: buildPlaythrough(),
      active_rule_check: null,
      active_minigame: null,
      pending_rule_check_trigger: null,
      is_narrating: false,
      last_client_action_id: null,
      cue_played_action_id: null,
      last_closed_rule_check_id: null,
      pending_client_effects: [],
      queued_client_effects: [],
      active_client_effect: null,
      effects_action_id: null,
      effects_generation: 0,
    });
  });

  it("is a full night: 21 turns that end in the recorded ending", () => {
    expect(turns).toHaveLength(NIGHT_TURNS);
    const ended = turns.flatMap((turn) => eventsNamed(turn, "playthrough_ended"));
    expect(ended).toHaveLength(1);
  });

  it("ends every turn with the visible state the server sent and no secrets", () => {
    for (const turn of turns) {
      replay(turn);
      const [update] = eventsNamed(turn, "state_update").slice(-1);
      const sent = (update.data as { state: Record<string, unknown> }).state;
      const stored = usePlayStore.getState().playthrough!.state;

      expect(stored.sanity).toBe(sent.sanity);
      expect(stored.shift_minutes).toBe(sent.shift_minutes);
      expect(Object.keys(stored).filter((key) => HIDDEN_ROOTS.includes(key))).toEqual(
        [],
      );
      expect(usePlayStore.getState().is_narrating).toBe(false);
    }
  });

  it("opens each prompt the server announced and closes it when it is answered", () => {
    for (const turn of turns) {
      replay(turn);
      const [check] = eventsNamed(turn, "check");
      const active = usePlayStore.getState().active_rule_check;
      if (check) {
        const payload = check.data as { check_id: string; kind: string };
        expect(active?.check_id).toBe(payload.check_id);
        expect(active?.kind).toBe(payload.kind);
      }
      if (turn.request.action_kind === "check_report" && !check) {
        expect(active).toBeNull();
      }
    }
  });

  it("performs every cue in the order it was sent, once", () => {
    for (const turn of turns) replay(turn);

    const sent = turns.flatMap((turn) =>
      eventsNamed(turn, "sensory_cue").map(
        (item) => (item.data as { cue: string }).cue,
      ),
    );
    expect(sent.length).toBeGreaterThan(0);
    expect(playedCues).toEqual(sent);
  });

  it("holds the Hum with its composure config", () => {
    const seen: string[] = [];
    for (const turn of turns) {
      replay(turn);
      const [minigame] = eventsNamed(turn, "minigame");
      if (!minigame) continue;
      const payload = minigame.data as { minigame_type: string };
      const active = usePlayStore.getState().active_minigame;
      expect(active?.minigame_type).toBe(payload.minigame_type);
      expect(active?.composure_config).toBeTruthy();
      seen.push(payload.minigame_type);
    }
    expect(seen).toEqual(["rhythm_composure"]);
  });

  it("plays every client effect once, after its turn commits", () => {
    const sent: string[] = [];
    const played: string[] = [];
    for (const turn of turns) {
      replay(turn);
      sent.push(
        ...eventsNamed(turn, "client_effect").map(
          (item) => (item.data as { kind: string }).kind,
        ),
      );
      while (usePlayStore.getState().active_client_effect) {
        played.push(usePlayStore.getState().active_client_effect!.kind);
        usePlayStore.getState().finishClientEffect();
      }
    }
    expect(sent.length).toBeGreaterThan(0);
    expect(played).toEqual(sent);
  });

  it("ends with the rules the night revealed and the ending recorded", () => {
    for (const turn of turns) replay(turn);

    const store = usePlayStore.getState().playthrough!;
    expect(store.rule_sheet).toHaveLength(REVEALED_RULE_COUNT);
    expect(store.ended_outcome_title).toBe("Mr. Orr Is In");
  });
});
