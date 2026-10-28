import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useStrategySituations } from "../useStrategySituations";
import { makeEventMemory, makePendingEvent, makeUprising } from "../../test-utils/eventFixtures";
import type { CampaignWorldView } from "../../types/simulation.types";

function worldWith(overrides: Partial<CampaignWorldView>): CampaignWorldView {
  return overrides as CampaignWorldView;
}

describe("useStrategySituations", () => {
  it("turns a pending event into an actionable situation with real numbers", () => {
    const world = worldWith({ pending_events: [makePendingEvent()] });
    const { result } = renderHook(() => useStrategySituations(world));
    const [situation] = result.current.situations;
    expect(situation.eventId).toBe("event_1");
    expect(situation.isActionable).toBe(true);
    expect(situation.regionId).toBe("ashford");
    expect(situation.severityStage).toBe(2);
    expect(situation.maxStage).toBe(3);
    expect(situation.severityLabel).toBe("Petition");
    expect(situation.causeQuote).toBe(
      "Because unrest is 62 and the governor's opinion of you is −40.",
    );
    expect(situation.deadlineTurn).toBe(5);
    expect(situation.ifIgnoredWarning).toContain("Unrest +10");
    expect(result.current.activeCrisesCount).toBe(1);
  });

  it("makes each event choice a lever with its order cost and effects", () => {
    const world = worldWith({ pending_events: [makePendingEvent()] });
    const { result } = renderHook(() => useStrategySituations(world));
    const [ease, crackdown] = result.current.situations[0].levers;
    expect(ease).toMatchObject({
      eventId: "event_1",
      choiceId: "ease_taxes",
      orderCost: 1,
      isAffordable: true,
      isQueued: false,
    });
    expect(ease.effects).toEqual(["Unrest −10", "Gold −20"]);
    expect(crackdown.orderCost).toBe(2);
  });

  it("marks the queued choice and carries its command id for cancelling", () => {
    const event = makePendingEvent({
      queued_choice_id: "ease_taxes",
      queued_command_id: "cmd-1",
    });
    const { result } = renderHook(() =>
      useStrategySituations(worldWith({ pending_events: [event] })),
    );
    const levers = result.current.situations[0].levers;
    expect(levers[0]).toMatchObject({ isQueued: true, queuedCommandId: "cmd-1" });
    expect(levers[1]).toMatchObject({ isQueued: false, queuedCommandId: null });
  });

  it("keeps an unaffordable choice visible but flagged", () => {
    const event = makePendingEvent();
    event.choices[1].is_affordable = false;
    const { result } = renderHook(() =>
      useStrategySituations(worldWith({ pending_events: [event] })),
    );
    expect(result.current.situations[0].levers[1].isAffordable).toBe(false);
  });

  it("shows a lingering problem with no pending event as ongoing and not actionable", () => {
    const world = worldWith({
      event_memories: [makeEventMemory({ last_tier: 2, scar: 15 })],
    });
    const { result } = renderHook(() => useStrategySituations(world));
    const [situation] = result.current.situations;
    expect(situation.isActionable).toBe(false);
    expect(situation.eventId).toBeNull();
    expect(situation.levers).toEqual([]);
    expect(situation.deadlineTurn).toBeNull();
    expect(situation.intelligence).toEqual(["Lingering resentment: 15"]);
  });

  it("does not list a memory twice when its event is still pending", () => {
    const world = worldWith({
      pending_events: [makePendingEvent()],
      event_memories: [makeEventMemory({ last_tier: 2 })],
    });
    const { result } = renderHook(() => useStrategySituations(world));
    expect(result.current.situations).toHaveLength(1);
  });

  it("ignores forgotten memories with no tier left", () => {
    const world = worldWith({ event_memories: [makeEventMemory({ last_tier: 0, scar: 4 })] });
    const { result } = renderHook(() => useStrategySituations(world));
    expect(result.current.situations).toEqual([]);
  });

  it("escalates the worst pending situation at stage two or above", () => {
    const world = worldWith({
      pending_events: [
        makePendingEvent({ id: "event_1", tier: 1 }),
        makePendingEvent({ id: "event_2", subject_id: "caldor", region_id: "caldor", tier: 3 }),
      ],
    });
    const { result } = renderHook(() => useStrategySituations(world));
    expect(result.current.escalatedSituation?.eventId).toBe("event_2");
  });

  it("has no escalated situation while every event is at stage one", () => {
    const world = worldWith({ pending_events: [makePendingEvent({ tier: 1 })] });
    const { result } = renderHook(() => useStrategySituations(world));
    expect(result.current.escalatedSituation).toBeNull();
  });

  it("pins a governor event to the governor's region and names it from the map", () => {
    const event = makePendingEvent({
      template_id: "noble_defiance",
      subject_kind: "governor",
      subject_id: "gov_harl",
      subject_name: "Lord Harl",
      region_id: "ashford",
    });
    const { result } = renderHook(() =>
      useStrategySituations(worldWith({ pending_events: [event] }), { ashford: "Ashford Vale" }),
    );
    expect(result.current.situations[0].regionId).toBe("ashford");
    expect(result.current.situations[0].regionName).toBe("Ashford Vale");
    expect(result.current.situations[0].title).toBe("Lord Harl defies the crown");
  });

  it("has no map pin for a faction-wide event", () => {
    const event = makePendingEvent({
      template_id: "realm_in_turmoil",
      subject_kind: "faction",
      subject_id: "house_carrow",
      subject_name: "House Carrow",
      region_id: null,
    });
    const { result } = renderHook(() =>
      useStrategySituations(worldWith({ pending_events: [event] })),
    );
    expect(result.current.situations[0].regionId).toBeNull();
  });

  it("does not invent situations from plain unrest", () => {
    const world = worldWith({ regions: [{ region_id: "ashford", unrest: 95 } as never] });
    const { result } = renderHook(() => useStrategySituations(world));
    expect(result.current.situations).toEqual([]);
  });

  it("handles a null or empty world gracefully", () => {
    const { result } = renderHook(() => useStrategySituations(null));
    expect(result.current.situations).toEqual([]);
    expect(result.current.activeCrisesCount).toBe(0);
    expect(result.current.escalatedSituation).toBeNull();
  });

  it("shows an uprising as a situation whose levers are its responses", () => {
    const world = worldWith({ uprisings: [makeUprising()] });
    const { result } = renderHook(() =>
      useStrategySituations(world, { ashford: "Ashford Vale" }),
    );
    const [situation] = result.current.situations;
    expect(situation.source).toBe("uprising");
    expect(situation.eventId).toBe("uprising_ashford_4");
    expect(situation.title).toBe("Petition from Ashford Vale");
    expect(situation.severityStage).toBe(1);
    expect(situation.maxStage).toBe(3);
    expect(situation.ifIgnoredWarning).toBe(
      "If unanswered within 2 turns, it will worsen to rioting.",
    );
    const [grant] = situation.levers;
    expect(grant).toMatchObject({
      source: "uprising",
      eventId: "uprising_ashford_4",
      choiceId: "concessions",
      orderCost: 1,
    });
    expect(grant.effects).toEqual([
      "Unrest −30",
      "Reputation −5",
      "Other restless provinces grow bolder (+5 unrest).",
    ]);
  });

  it("warns that an armed uprising will cost the region and raises the banner", () => {
    const uprising = makeUprising({
      stage: "armed",
      is_final_stage: true,
      rebel_troops: 50,
      turns_until_change: 1,
      queued_response: "restore_order",
      queued_command_id: "cmd-9",
    });
    const { result } = renderHook(() =>
      useStrategySituations(worldWith({ uprisings: [uprising] })),
    );
    const [situation] = result.current.situations;
    expect(situation.ifIgnoredWarning).toBe(
      "If unanswered next turn, the region will be lost to the crown.",
    );
    expect(situation.intelligence[0]).toBe("Rebels hold the region with 50 men");
    expect(situation.levers[1]).toMatchObject({ isQueued: true, queuedCommandId: "cmd-9" });
    expect(result.current.escalatedSituation?.eventId).toBe("uprising_ashford_4");
  });
});
