import { describe, it, expect } from "vitest";
import { buildPendingEventPackage } from "../pendingEventPackage";
import { makePendingEvent, makeUprising } from "../../test-utils/eventFixtures";
import type { CampaignWorldView } from "../../types/simulation.types";

function worldWith(events = [makePendingEvent()]): CampaignWorldView {
  return {
    turn: 5,
    clock: { turn: 5, start_year: 1042, start_month: 1 },
    pending_events: events,
  } as CampaignWorldView;
}

describe("buildPendingEventPackage", () => {
  it("returns null when no event is selected or it no longer exists", () => {
    expect(buildPendingEventPackage(worldWith(), null)).toBeNull();
    expect(buildPendingEventPackage(worldWith(), "event_404")).toBeNull();
    expect(buildPendingEventPackage({ turn: 1 } as CampaignWorldView, "event_1")).toBeNull();
  });

  it("builds the dialog package from server data only", () => {
    const pkg = buildPendingEventPackage(worldWith(), "event_1");
    expect(pkg).toMatchObject({
      eventId: "event_1",
      title: "Grievance in Ashford Vale",
      turnText: "Turn 5 • Year 1042",
      neglectWarning: "Unrest +10, Governor opinion −10",
      queuedChoiceId: null,
    });
    expect(pkg?.choices.map((choice) => choice.id)).toEqual([
      "ease_taxes",
      "garrison_crackdown",
    ]);
    expect(pkg?.choices[0]).toMatchObject({
      label: "Lighten the levy in this region",
      orderCost: 1,
      isAffordable: true,
      effects: ["Unrest −10", "Gold −20"],
    });
  });

  it("carries a queued answer so the dialog can show and cancel it", () => {
    const event = makePendingEvent({ queued_choice_id: "ease_taxes", queued_command_id: "cmd-3" });
    const pkg = buildPendingEventPackage(worldWith([event]), "event_1");
    expect(pkg?.queuedChoiceId).toBe("ease_taxes");
    expect(pkg?.queuedCommandId).toBe("cmd-3");
  });
});

describe("buildPendingEventPackage for an uprising", () => {
  it("builds the manuscript package from the uprising and its responses", () => {
    const world = { turn: 5, uprisings: [makeUprising()] } as unknown as CampaignWorldView;
    const pkg = buildPendingEventPackage(world, "uprising_ashford_4", { ashford: "Ashford Vale" });
    expect(pkg).toMatchObject({
      source: "uprising",
      eventId: "uprising_ashford_4",
      title: "Petition from Ashford Vale",
      causeQuote: "Because unrest in Ashford Vale reached 78.",
    });
    expect(pkg?.choices.map((choice) => choice.id)).toEqual(["concessions", "restore_order"]);
  });
});
