import { describe, it, expect } from "vitest";
import {
  buildMasterPlaythroughData,
  buildNewbiePlaythroughData,
} from "../playthroughDataBuilders";
import { PlaythroughResponse } from "@/shared/api/playthroughs.api";
import { TurnLogListResponse } from "../../api/turns.api";

function buildServerPlaythrough(
  overrides: Partial<PlaythroughResponse> = {},
): PlaythroughResponse {
  return {
    playthrough_id: "pt-1",
    scenario_id: "sc-1",
    scenario_title: "The Hollow Cairn",
    created_by: "user-1",
    state: {
      player: { health: 85, sanity: 98, inventory: ["sword-1"] },
      entities: { "warden-1": { awareness: 40 } },
    },
    checkpoint: null,
    turn_count: 0,
    status: "active",
    scenario_version: 1,
    scenario_snapshot: {
      mode: "master",
      setup_schema: [],
      state_schema: {
        player: {
          type: "object",
          fields: {
            health: { type: "number", label: "Health" },
            sanity: { type: "number" },
            inventory: { type: "list", item_type: "entity_ref" },
          },
        },
      },
      entities: [
        {
          entity_id: "warden-1",
          entity_type: "character",
          canonical_name: "The Warden",
          aliases: [],
          description: null,
          attributes_schema: { awareness: { type: "number" } },
          obtainable: null,
        },
        {
          entity_id: "sword-1",
          entity_type: "item",
          canonical_name: "Rusty Sword",
          aliases: [],
          description: null,
          attributes_schema: {},
          obtainable: true,
        },
      ],
      end_conditions: [
        {
          outcome_tag: "win",
          outcome_title: "The Ashen Ending",
          outcome_text: "The Warden kneels.",
          is_secret: false,
        },
        {
          outcome_tag: "win",
          outcome_title: "The Vigil's Ending",
          outcome_text: "You relieve it.",
          is_secret: true,
        },
      ],
      facts: [
        { fact_id: "fact-1", text: "The Warden guards the Rusty Sword." },
      ],
    },
    created_at: "2026-10-27T00:00:00Z",
    updated_at: "2026-10-27T00:00:00Z",
    participant_id: "participant-1",
    server_time_ms: 1_760_000_000_000,
    participants: [
      {
        participant_id: "participant-1",
        user_id: "u1",
        role: "owner",
        turn_order_position: 1,
      },
    ],
    active_conditions: ["Bleeding Out"],
    ended_outcome_tag: null,
    ended_outcome_title: null,
    ended_outcome_text: null,
    ...overrides,
  };
}

const emptyTurns: TurnLogListResponse = { items: [], total_count: 0 };

describe("buildMasterPlaythroughData", () => {
  it("merges live entity attributes onto the pinned snapshot entities", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    const warden = data.entities.find((e) => e.entity_id === "warden-1");
    expect(warden?.attributes).toEqual({ awareness: 40 });
  });

  it("builds player_stats from non-list/non-entity_ref state_schema.player fields", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.player_stats).toEqual([
      { key: "health", label: "Health", value: 85 },
      { key: "sanity", label: "Sanity", value: 98 },
    ]);
  });

  it("maps the pinned snapshot facts into key_facts", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.key_facts).toEqual(["The Warden guards the Rusty Sword."]);
  });

  it("resolves player_inventory entity ids against the entities list", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.player_inventory).toHaveLength(1);
    expect(data.player_inventory[0].canonical_name).toBe("Rusty Sword");
  });

  it("filters secret end_conditions out of objectives", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.objectives).toEqual([
      {
        outcome_title: "The Ashen Ending",
        outcome_tag: "win",
        outcome_text: "The Warden kneels.",
      },
    ]);
  });

  it("uses the rendered opening scene from state.narrative when present", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        state: {
          player: {},
          narrative: { opening_prompt: "Good evening, Mara." },
        },
      }),
      emptyTurns,
      false,
    );

    expect(data.opening_premise).toBe("Good evening, Mara.");
  });

  it("falls back to the default premise when no opening scene was rendered", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        state: { player: {}, narrative: { opening_prompt: null } },
      }),
      emptyTurns,
      false,
    );

    expect(data.opening_premise).toBe("Your chronicle begins...");
  });

  it("builds the same view from the server's allowlisted client snapshot", () => {
    const full = buildServerPlaythrough();
    const clientSnapshot = {
      ...full.scenario_snapshot,
      enabled_tools: [],
      end_conditions: [
        {
          outcome_title: "The Ashen Ending",
          outcome_tag: "win",
          outcome_text: "The Warden kneels.",
        },
      ],
    };

    const fromFull = buildMasterPlaythroughData(full, emptyTurns, false);
    const fromClient = buildMasterPlaythroughData(
      buildServerPlaythrough({ scenario_snapshot: clientSnapshot }),
      emptyTurns,
      false,
    );

    expect(fromClient).toEqual(fromFull);
  });

  it("reads string duties from world_data, at most four", () => {
    const base = buildServerPlaythrough();
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        scenario_snapshot: {
          ...base.scenario_snapshot,
          world_data: { duties: ["a", 3, "b", "c", "d", "e"] },
        },
      }),
      emptyTurns,
      false,
    );

    expect(data.duties).toEqual(["a", "b", "c", "d"]);
  });

  it("has no duties when world_data has none", () => {
    const data = buildMasterPlaythroughData(buildServerPlaythrough(), emptyTurns, false);
    expect(data.duties).toEqual([]);
  });

  it("reads enabled_tools from the pinned snapshot", () => {
    const base = buildServerPlaythrough();
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        scenario_snapshot: {
          ...base.scenario_snapshot,
          enabled_tools: ["rule_checks", "status_hud"],
        },
      }),
      emptyTurns,
      false,
    );

    expect(data.enabled_tools).toEqual(["rule_checks", "status_hud"]);
  });

  it("treats a snapshot without enabled_tools as having no tools", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.enabled_tools).toEqual([]);
  });

  it("ignores malformed enabled_tools values", () => {
    const base = buildServerPlaythrough();
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        scenario_snapshot: {
          ...base.scenario_snapshot,
          enabled_tools: ["rule_checks", 7, null],
        },
      }),
      emptyTurns,
      false,
    );

    expect(data.enabled_tools).toEqual(["rule_checks"]);
  });

  it("opens a newbie playthrough with the rendered opening scene from state.narrative", () => {
    const data = buildNewbiePlaythroughData(
      buildServerPlaythrough({
        scenario_snapshot: {
          mode: "newbie",
          world_data: { openingPrompt: "Legacy opening." },
        },
        state: { narrative: { opening_prompt: "Good evening, Mara." } },
      }),
      emptyTurns,
      false,
    );

    expect(data.opening_premise).toBe("Good evening, Mara.");
  });

  it("keeps the legacy openingPrompt for newbie playthroughs without a rendered scene", () => {
    const data = buildNewbiePlaythroughData(
      buildServerPlaythrough({
        scenario_snapshot: {
          mode: "newbie",
          world_data: { openingPrompt: "Legacy opening." },
        },
        state: {},
      }),
      emptyTurns,
      false,
    );

    expect(data.opening_premise).toBe("Legacy opening.");
  });

  it("gives newbie playthroughs no tools", () => {
    const data = buildNewbiePlaythroughData(
      buildServerPlaythrough({ scenario_snapshot: { mode: "newbie" } }),
      emptyTurns,
      false,
    );

    expect(data.enabled_tools).toEqual([]);
  });

  it("reads an open rule check from state._pending_check", () => {
    const pending = {
      check_id: "chk-1",
      kind: "timed_choice",
      check_def_id: "def-1",
      prompt: "The phone rings.",
      options: [{ id: "answer", label: "Answer it" }],
      window_ms: 12000,
      issued_at: 1_760_000_000_000,
      resolved: null,
    };
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        state: { player: {}, _pending_check: pending },
        server_time_ms: 1_760_000_004_000,
      }),
      emptyTurns,
      false,
    );

    expect(data.pending_rule_check?.check_id).toBe("chk-1");
    expect(data.pending_rule_check?.options).toEqual([
      { id: "answer", label: "Answer it" },
    ]);
    expect(data.server_time_ms).toBe(1_760_000_004_000);
  });

  it("does not mistake a rule check for a dice check", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        state: {
          player: {},
          _pending_check: { check_id: "chk-1", kind: "timed_choice" },
        },
      }),
      emptyTurns,
      false,
    );

    expect(data.pending_check).toBeNull();
  });

  it("does not mistake a dice check for a rule check", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        state: {
          player: {},
          _pending_check: {
            check_id: "chk-2",
            check_type: "stealth",
            difficulty_class: 12,
            resolved_roll: null,
          },
        },
      }),
      emptyTurns,
      false,
    );

    expect(data.pending_rule_check).toBeNull();
    expect(data.pending_check?.check_id).toBe("chk-2");
  });

  it("copies the visible state onto the playthrough for the HUD", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({ state: { player: { health: 5 }, shift: 30 } }),
      emptyTurns,
      false,
    );

    expect(data.state).toEqual({ player: { health: 5 }, shift: 30 });
  });

  it("reads display hints from the pinned state_schema", () => {
    const base = buildServerPlaythrough();
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        scenario_snapshot: {
          ...base.scenario_snapshot,
          state_schema: {
            shift_minutes: {
              type: "number",
              display: {
                kind: "clock",
                label: "Shift",
                start: "23:00",
                format: "12h",
              },
            },
          },
        },
      }),
      emptyTurns,
      false,
    );

    expect(data.hud_hints.clock?.path).toBe("shift_minutes");
  });

  it("has no hud hints for a schema without them", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.hud_hints).toEqual({ meters: [] });
  });

  it("carries active_conditions through from the server response", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.active_conditions).toEqual(["Bleeding Out"]);
  });

  it("carries the ended outcome through from the server response", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        ended_outcome_tag: "win",
        ended_outcome_title: "The Ashen Ending",
        ended_outcome_text: "The Warden kneels.",
      }),
      emptyTurns,
      false,
    );

    expect(data.ended_outcome_tag).toBe("win");
    expect(data.ended_outcome_title).toBe("The Ashen Ending");
    expect(data.ended_outcome_text).toBe("The Warden kneels.");
  });

  it("defaults the ended outcome to null for an in-progress playthrough", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.ended_outcome_tag).toBeNull();
  });

  it("parses pending_minigame from state._pending_minigame when present", () => {
    const pendingMinigame = {
      minigame_id: "mg-1",
      minigame_type: "dodge",
      label: "Rune Puzzle",
      dodge_config: { difficulty: 3 },
      timeout_seconds: 20,
    };
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough({
        state: {
          player: { health: 85, sanity: 98, inventory: ["sword-1"] },
          entities: { "warden-1": { awareness: 40 } },
          _pending_minigame: pendingMinigame,
        },
      }),
      emptyTurns,
      false,
    );

    expect(data.pending_minigame).toEqual(pendingMinigame);
  });

  it("defaults pending_minigame to null when state has no pending marker", () => {
    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      emptyTurns,
      false,
    );

    expect(data.pending_minigame).toBeNull();
  });

  it("extracts narration_font from scenario_snapshot", () => {
    const serverPt = buildServerPlaythrough({
      scenario_snapshot: {
        mode: "master",
        narration_font: "special-elite",
      },
    });
    const data = buildMasterPlaythroughData(serverPt, emptyTurns, false);
    expect(data.narration_font).toBe("special-elite");
  });

  it("preserves the server-recorded action_mode on each turn", () => {
    const turns: TurnLogListResponse = {
      items: [
        {
          turn_id: "turn-1",
          playthrough_id: "pt-1",
          turn_number: 1,
          participant_id: "participant-1",
          action_text: "I whisper to the Warden.",
          action_mode: "say",
          narration_text: "The Warden stirs.",
          tool_calls: [],
          created_at: "2026-10-27T00:00:00Z",
          image_url: null,
          audio_url: null,
        },
      ],
      total_count: 1,
    };

    const data = buildMasterPlaythroughData(
      buildServerPlaythrough(),
      turns,
      false,
    );

    expect(data.turns[0].action_mode).toBe("say");
  });
});
