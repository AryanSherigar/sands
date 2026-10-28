import { describe, it, expect } from "vitest";
import {
  describeCause,
  describeEffect,
  describeEffects,
  describeIntelligence,
  describeNeglect,
  narrate,
  stageLabel,
  stageLabels,
  toStage,
} from "../eventText";
import { makePendingEvent } from "../../test-utils/eventFixtures";

describe("eventText", () => {
  it("writes signed effects with a real minus sign", () => {
    expect(describeEffect({ kind: "gold", amount: -20 })).toBe("Gold −20");
    expect(describeEffect({ kind: "stability", amount: 3 })).toBe("Stability +3");
    expect(describeEffects([{ kind: "army_morale", amount: 15 }])).toEqual(["Army morale +15"]);
  });

  it("labels unknown effect kinds instead of hiding them", () => {
    expect(describeEffect({ kind: "mystery_kind", amount: 2 })).toBe("mystery kind +2");
  });

  it("builds the cause line only from numbers the server sent", () => {
    expect(describeCause({ region_unrest: 62, governor_opinion: -40 })).toBe(
      "Because unrest is 62 and the governor's opinion of you is −40.",
    );
    expect(describeCause({ army_unpaid_turns: 1 })).toBe("Because pay is 1 turn overdue.");
    expect(describeCause({ army_unpaid_turns: 3 })).toBe("Because pay is 3 turns overdue.");
  });

  it("explains a faction-wide event by how many provinces are restless", () => {
    expect(describeCause({ regions_with_unrest_at_least: 2, stability: 66 })).toBe(
      "Because 2 provinces are in open unrest and stability is 66.",
    );
  });

  it("gives no cause line for inputs it has no wording for", () => {
    expect(describeCause({ tier: 2, something_else: 9 })).toBe("");
    expect(describeCause({})).toBe("");
  });

  it("lists intelligence as capitalised facts", () => {
    expect(describeIntelligence({ region_unrest: 62 })).toEqual(["Unrest is 62"]);
  });

  it("joins the neglect outcome and handles none", () => {
    expect(
      describeNeglect([
        { kind: "region_unrest", amount: 10 },
        { kind: "governor_opinion", amount: -10 },
      ]),
    ).toBe("Unrest +10, Governor opinion −10");
    expect(describeNeglect([])).toBe("");
  });

  it("labels stages per template and falls back for unknown ones", () => {
    expect(stageLabel("tax_grievance", 1)).toBe("Murmurs");
    expect(stageLabel("unpaid_mutiny", 3)).toBe("Open mutiny");
    expect(stageLabel("custom_event", 2)).toBe("Stage 2");
    expect(stageLabels("noble_defiance", 3)).toEqual(["Resentful", "Defiant", "On the brink"]);
  });

  it("keeps the stage inside one to four", () => {
    expect(toStage(0)).toBe(1);
    expect(toStage(3)).toBe(3);
    expect(toStage(9)).toBe(4);
  });

  it("narrates a known event from its subject and tier", () => {
    const narrative = narrate(makePendingEvent({ tier: 3 }));
    expect(narrative.title).toBe("Grievance in Ashford Vale");
    expect(narrative.disposition).toBe("Defiant");
    expect(narrative.causeQuote).toContain("unrest is 62");
  });

  it("narrates an unknown template generically without crashing", () => {
    const narrative = narrate(makePendingEvent({ template_id: "custom_event", tier: 1 }));
    expect(narrative.title).toBe("Ashford Vale");
    expect(narrative.disposition).toBe("Troubled");
  });
});
