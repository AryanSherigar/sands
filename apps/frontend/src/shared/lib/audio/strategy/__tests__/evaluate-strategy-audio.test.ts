import { describe, it, expect } from "vitest";
import { evaluateStrategyAudio } from "../evaluate-strategy-audio";
import type { StrategyWorldSnapshot } from "@/features/play/types/strategyPlay.types";

const mockBaseWorld: StrategyWorldSnapshot = {
  playthrough_id: "test-playthrough",
  turn: 1,
  season: "spring",
  year: 1042,
  status: "active",
  orders_remaining: 3,
  my_faction: {
    id: "f_crown",
    name: "Crown of High Cairn",
    treasury: 120,
    ruler: { name: "King Lucan", health_band: "robust" },
    capital_region_id: "reg_cairn",
    stats: { military: 50, economy: 60, diplomacy: 50 },
  },
  regions: [
    {
      id: "reg_cairn",
      name: "High Cairn",
      owner_faction_id: "f_crown",
      terrain: "mountains",
      unrest: 10,
      manpower: 500,
      is_under_siege: false,
    },
  ],
  armies: [],
  wars: [],
  rivals: [],
  event_log: [],
  queued_orders: [],
};

describe("evaluateStrategyAudio", () => {
  it("evaluates peaceful prosperity into Pax tier", () => {
    const target = evaluateStrategyAudio(mockBaseWorld, "map", "seed-123");
    expect(target.strategicMood).toBe("pax");
    expect(target.moodGain).toBe(0.6);
    expect(target.contextGain).toBe(0.0);
    expect(target.ambientTrack).toBe("mountains");
    expect(target.isWinterMuffled).toBe(false);
  });

  it("muffles ambient audio when season is winter", () => {
    const winterWorld: StrategyWorldSnapshot = {
      ...mockBaseWorld,
      season: "winter",
    };
    const target = evaluateStrategyAudio(winterWorld, "map", "seed-123");
    expect(target.isWinterMuffled).toBe(true);
  });

  it("escalates to War tier when player is involved in active war", () => {
    const warWorld: StrategyWorldSnapshot = {
      ...mockBaseWorld,
      wars: [
        {
          war_id: "war-1",
          attacker_faction_id: "f_iron",
          defender_faction_id: "f_crown",
          war_score: -10,
        },
      ],
    };
    const target = evaluateStrategyAudio(warWorld, "map", "seed-123");
    expect(target.strategicMood).toBe("war");
    expect(target.moodGain).toBe(0.7);
  });

  it("escalates war intensity under siege and maintains war tier", () => {
    const siegeWorld: StrategyWorldSnapshot = {
      ...mockBaseWorld,
      wars: [
        {
          war_id: "war-1",
          attacker_faction_id: "f_iron",
          defender_faction_id: "f_crown",
          war_score: -10,
        },
      ],
      regions: [
        {
          ...mockBaseWorld.regions![0],
          is_under_siege: true,
          siege_progress: 2,
        },
      ],
    };
    const target = evaluateStrategyAudio(siegeWorld, "map", "seed-123");
    expect(target.strategicMood).toBe("war");
    expect(target.moodGain).toBe(0.7);
  });

  it("escalates to Desolation tier when unrest is severe or treasury in deep debt", () => {
    const crisisWorld: StrategyWorldSnapshot = {
      ...mockBaseWorld,
      my_faction: {
        ...mockBaseWorld.my_faction!,
        treasury: -50,
      },
      regions: [
        {
          ...mockBaseWorld.regions![0],
          unrest: 85,
        },
      ],
    };
    const target = evaluateStrategyAudio(crisisWorld, "map", "seed-123");
    expect(target.strategicMood).toBe("desolation");
    expect(target.moodGain).toBe(0.6);
  });

  it("escalates to Vigilance tier during moderate strain without full war", () => {
    const tenseWorld: StrategyWorldSnapshot = {
      ...mockBaseWorld,
      regions: [
        {
          ...mockBaseWorld.regions![0],
          unrest: 45,
        },
      ],
    };
    const target = evaluateStrategyAudio(tenseWorld, "map", "seed-123");
    expect(target.strategicMood).toBe("vigilance");
    expect(target.moodGain).toBe(0.5);
  });

  it("ducks mood and activates Layer 3 tint when in negotiation, letter, or war council", () => {
    const targetNegotiation = evaluateStrategyAudio(mockBaseWorld, "negotiation", "seed-123");
    expect(targetNegotiation.contextTrack).toBe("court");
    expect(targetNegotiation.contextGain).toBe(0.4);
    expect(targetNegotiation.moodGain).toBe(0.3); // 0.6 * 0.5 ducking

    const targetLetter = evaluateStrategyAudio(mockBaseWorld, "letter", "seed-123");
    expect(targetLetter.contextTrack).toBe("study");
    expect(targetLetter.contextGain).toBe(0.45);
    expect(targetLetter.moodGain).toBeCloseTo(0.24); // 0.6 * 0.4 ducking

    const targetWarCouncil = evaluateStrategyAudio(mockBaseWorld, "war_council", "seed-123");
    expect(targetWarCouncil.contextTrack).toBe("tactical");
    expect(targetWarCouncil.contextGain).toBe(0.5);
    expect(targetWarCouncil.moodGain).toBeCloseTo(0.36); // 0.6 * 0.6 ducking

    const targetTurnReport = evaluateStrategyAudio(mockBaseWorld, "turn_report", "seed-123");
    expect(targetTurnReport.contextTrack).toBe("none");
    expect(targetTurnReport.contextGain).toBe(0.0);
    expect(targetTurnReport.moodGain).toBeCloseTo(0.42); // 0.6 * 0.7 ducking

    const targetEvent = evaluateStrategyAudio(mockBaseWorld, "event", "seed-123");
    expect(targetEvent.contextTrack).toBe("court");
    expect(targetEvent.contextGain).toBe(0.3);
    expect(targetEvent.moodGain).toBeCloseTo(0.3); // 0.6 * 0.5 ducking
  });

  it("detects single-shot event stingers from latest turn event log", () => {
    const makeWorldWithEvent = (eventType: string): StrategyWorldSnapshot => ({
      ...mockBaseWorld,
      turn: 5,
      event_log: [
        {
          turn: 5,
          event_type: eventType,
          description: `Event of type ${eventType}`,
        },
      ],
    });

    expect(evaluateStrategyAudio(makeWorldWithEvent("WAR_DECLARED"), "map", "seed-123", 4).pendingStinger).toBe(
      "war_declared",
    );
    expect(evaluateStrategyAudio(makeWorldWithEvent("TREATY_SIGNED"), "map", "seed-123", 4).pendingStinger).toBe(
      "treaty_signed",
    );
    expect(evaluateStrategyAudio(makeWorldWithEvent("UPRISING_STARTED"), "map", "seed-123", 4).pendingStinger).toBe(
      "uprising",
    );
    expect(evaluateStrategyAudio(makeWorldWithEvent("SUCCESSION_HEIR"), "map", "seed-123", 4).pendingStinger).toBe(
      "succession",
    );
  });

  it("ignores stingers that occurred on or before lastPlayedTurn", () => {
    const worldWithOldEvent: StrategyWorldSnapshot = {
      ...mockBaseWorld,
      turn: 5,
      event_log: [
        {
          turn: 5,
          event_type: "WAR_DECLARED",
        },
      ],
    };
    const target = evaluateStrategyAudio(worldWithOldEvent, "map", "seed-123", 5);
    expect(target.pendingStinger).toBeNull();
  });

  it("resolves terrain defaults and variants correctly", () => {
    const makeWorldWithTerrain = (terrain: string): StrategyWorldSnapshot => ({
      ...mockBaseWorld,
      regions: [
        {
          id: "reg_cairn",
          owner_faction_id: "f_crown",
          terrain,
        },
      ],
    });

    expect(evaluateStrategyAudio(makeWorldWithTerrain("desert_dune"), "map", "s").ambientTrack).toBe("arid");
    expect(evaluateStrategyAudio(makeWorldWithTerrain("coastal_bay"), "map", "s").ambientTrack).toBe("coast");
    expect(evaluateStrategyAudio(makeWorldWithTerrain("rocky_mountains"), "map", "s").ambientTrack).toBe(
      "mountains",
    );
    expect(evaluateStrategyAudio(makeWorldWithTerrain("grassland_plains"), "map", "s").ambientTrack).toBe("plains");
    expect(evaluateStrategyAudio(makeWorldWithTerrain("unknown_forest"), "map", "s").ambientTrack).toBe("plains");
  });

  it("proves strict mathematical determinism across repeated calls", () => {
    const first = evaluateStrategyAudio(mockBaseWorld, "map", "seed-constant");
    const second = evaluateStrategyAudio(mockBaseWorld, "map", "seed-constant");
    expect(first).toEqual(second);
  });
});
