import { describe, expect, it } from "vitest";
import {
  addFaction,
  applyStrategyFields,
  getRegionOwner,
  makeUniqueId,
  readStrategyFields,
  removeFaction,
  setLeaderAmbitionPreset,
  setRegionOwner,
} from "./strategyDocument";

const empty = readStrategyFields({});

describe("strategyDocument", () => {
  it("builds a unique valid id from a name", () => {
    expect(makeUniqueId("House Ashford!", [])).toBe("house_ashford");
    expect(makeUniqueId("House Ashford", ["house_ashford"])).toBe("house_ashford_2");
    expect(makeUniqueId("7th Host", [])).toBe("f_7th_host");
  });

  it("adds a faction with a ready leader and ambition, first one playable", () => {
    const fields = addFaction(addFaction(empty, "Ashford"), "Carrow");

    expect(fields.factions.map((item) => item.is_playable)).toEqual([true, false]);
    expect(fields.leaders[0].faction_id).toBe("ashford");
    expect(fields.leaders[0].ambition_ids).toEqual(["ashford_expand"]);
    expect(fields.leaders[0].trait_ids).toHaveLength(2);
    expect(fields.ambitions[0].condition.subject_id).toBe("ashford");
  });

  it("switches a leader's ambition preset without leaving the old one behind", () => {
    const fields = setLeaderAmbitionPreset(addFaction(empty, "Ashford"), "ashford_ruler", "rich");

    expect(fields.ambitions.map((item) => item.id)).toEqual(["ashford_rich"]);
    expect(fields.leaders[0].ambition_ids).toEqual(["ashford_rich"]);
  });

  it("removes a faction with its leader, ambition and region ownership", () => {
    const owned = setRegionOwner(addFaction(empty, "Ashford"), "north", "ashford");
    const fields = removeFaction(owned, "ashford");

    expect(fields.factions).toEqual([]);
    expect(fields.leaders).toEqual([]);
    expect(fields.ambitions).toEqual([]);
    expect(getRegionOwner(fields, "north")).toBeNull();
  });

  it("keeps untouched document keys when applying edits", () => {
    const raw = { map: { regions: [] }, starting: { armies: [1] }, theme: { a: 1 } };
    const applied = applyStrategyFields(raw, addFaction(readStrategyFields(raw), "Ashford"));

    expect(applied.map).toEqual(raw.map);
    expect(applied.theme).toEqual(raw.theme);
    expect((applied.starting as { armies: number[] }).armies).toEqual([1]);
  });

  it("reads and round-trips system toggles, endings, and pacing tuning", () => {
    const raw = {
      toggles: { is_loans_enabled: false, is_ai_peace_enabled: false },
      is_using_default_endings: false,
      endings: [
        {
          id: "win_rich",
          kind: "victory",
          name: "Golden Horde",
          condition: { kind: "comparison", metric: "treasury", operator: "gte", value: 1000, subject_id: null },
          epilogue_hint: "Treasury overflowed.",
        },
      ],
      disabled_builtin_event_ids: ["plague", "bad_harvest"],
      tuning: {
        orders_per_turn: 8,
        event_frequency_percent: 75,
        endings: { toggles: { is_hegemony_enabled: false } },
      },
    };

    const fields = readStrategyFields(raw);
    expect(fields.toggles.is_loans_enabled).toBe(false);
    expect(fields.toggles.is_ai_peace_enabled).toBe(false);
    expect(fields.toggles.is_events_enabled).toBe(true);
    expect(fields.is_using_default_endings).toBe(false);
    expect(fields.endings).toHaveLength(1);
    expect(fields.endings[0].name).toBe("Golden Horde");
    expect(fields.disabled_builtin_event_ids).toEqual(["plague", "bad_harvest"]);
    expect(fields.orders_per_turn).toBe(8);
    expect(fields.event_frequency_percent).toBe(75);
    expect(fields.ending_toggles.is_hegemony_enabled).toBe(false);
    expect(fields.ending_toggles.is_regime_fall_enabled).toBe(true);

    const applied = applyStrategyFields(raw, fields) as Record<string, unknown>;
    expect(applied.is_using_default_endings).toBe(false);
    expect(applied.endings).toEqual(fields.endings);
    expect(applied.disabled_builtin_event_ids).toEqual(["plague", "bad_harvest"]);
    const appliedTuning = applied.tuning as Record<string, unknown>;
    expect(appliedTuning.orders_per_turn).toBe(8);
    expect(appliedTuning.event_frequency_percent).toBe(75);
    const appliedEndings = appliedTuning.endings as { toggles: Record<string, boolean> };
    expect(appliedEndings.toggles.is_hegemony_enabled).toBe(false);
  });

  it("reads and writes the letters and judgments settings without touching untouched ones", () => {
    const raw = { tuning: { letters: { is_enabled: true, cooldown_turns: 3 }, judgments: { is_enabled: false } } };

    const fields = readStrategyFields(raw);
    expect(fields.rules).toMatchObject({
      letters_enabled: true,
      letter_cooldown_turns: 3,
      judgments_enabled: false,
      judgment_cooldown_turns: 6,
      judgment_sentence_turns: 6,
    });

    const unchanged = applyStrategyFields(raw, fields) as { tuning: Record<string, unknown> };
    expect(unchanged.tuning.judgments).toEqual({ is_enabled: false });

    const edited = applyStrategyFields(raw, { ...fields, rules: { ...fields.rules, judgments_enabled: true, judgment_sentence_turns: 9 } }) as {
      tuning: { judgments: Record<string, unknown>; letters: Record<string, unknown> };
    };
    expect(edited.tuning.judgments).toEqual({ is_enabled: true, sentence_turns: 9 });
    expect(edited.tuning.letters).toEqual({ is_enabled: true, cooldown_turns: 3 });
  });

  it("preserves stance_ids on factions and heirs on leaders", () => {
    const raw = {
      factions: [
        {
          id: "ashford",
          name: "Ashford",
          color: "#8b2e2e",
          capital_region_id: null,
          leader_id: "ashford_ruler",
          treasury: 100,
          manpower: 400,
          stability: 60,
          is_playable: true,
          stance_ids: ["turtle"],
        },
      ],
      leaders: [
        {
          id: "ashford_ruler",
          name: "Lord Ashford",
          faction_id: "ashford",
          trait_ids: ["cautious"],
          ambition_ids: [],
          history: "",
          age: 45,
          heir: { id: "ashford_heir", name: "Young Ashford", age: 16, trait_ids: ["proud"] },
        },
      ],
    };

    const fields = readStrategyFields(raw);
    expect(fields.factions[0].stance_ids).toEqual(["turtle"]);
    expect(fields.leaders[0].heir?.name).toBe("Young Ashford");

    const applied = applyStrategyFields(raw, fields) as typeof raw;
    expect(applied.factions[0].stance_ids).toEqual(["turtle"]);
    expect(applied.leaders[0].heir?.name).toBe("Young Ashford");
  });
});
