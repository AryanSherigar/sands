import { describe, expect, it } from "vitest";
import { deriveTurnReport } from "../turnReportAdapter";
import { mergeTurnReport } from "../turnReportMerge";
import { isEventLine, toEventReportItem } from "../eventReportItems";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import type { ApiReportLine, TurnReportResponse } from "../../types/turnReportApi.types";

const REGION_NAMES = { elmstead: "Elmstead" };

function eventLine(kind: string, summaryKey: string, inputs = {}): ApiReportLine {
  return {
    text_key: summaryKey,
    kind,
    subject_ids: ["elmstead"],
    cause: { summary_key: summaryKey, subject_ids: ["elmstead"], inputs },
  };
}

describe("event report items", () => {
  it("recognises only event lines that carry an events.* key", () => {
    expect(isEventLine(eventLine("event_fired", "events.tax_grievance"))).toBe(true);
    expect(isEventLine({ text_key: "tax_rate_set", kind: "tax_rate_set", subject_ids: [] })).toBe(
      false,
    );
  });

  it("describes new trouble with its real cause", () => {
    const item = toEventReportItem(
      eventLine("event_fired", "events.tax_grievance", { region_unrest: 61, tier: 1 }),
      0,
      REGION_NAMES,
    );
    expect(item.title).toBe("Trouble: Grievance in Elmstead");
    expect(item.description).toBe("Because unrest is 61.");
    expect(item.category).toBe("internal");
    expect(item.regionId).toBe("elmstead");
    expect(item.badge?.tone).toBe("warning");
  });

  it("names the choice the player made", () => {
    const item = toEventReportItem(
      eventLine("event_answered", "events.tax_grievance.garrison_crackdown", { region_unrest: 61 }),
      1,
      REGION_NAMES,
    );
    expect(item.title).toBe("Answered: Grievance in Elmstead");
    expect(item.description).toBe("Garrison crackdown. Because unrest is 61.");
    expect(item.badge).toEqual({ label: "Garrison crackdown", tone: "positive" });
  });

  it("flags neglect as a danger", () => {
    const item = toEventReportItem(
      eventLine("event_neglected", "events.tax_grievance.neglected", { region_unrest: 73 }),
      2,
      REGION_NAMES,
    );
    expect(item.title).toBe("Neglected: Grievance in Elmstead");
    expect(item.description).toContain("Left unanswered");
    expect(item.description).toContain("Because unrest is 73.");
    expect(item.badge?.tone).toBe("danger");
  });

  it("falls back to a readable name for subjects that are not map regions", () => {
    const line: ApiReportLine = {
      text_key: "events.noble_defiance",
      kind: "event_fired",
      subject_ids: ["gov_danica"],
    };
    const item = toEventReportItem(line, 0, REGION_NAMES);
    expect(item.title).toBe("Trouble: Gov danica defies the crown");
    expect(item.regionId).toBeUndefined();
  });

  it("puts event cards into the merged turn report", () => {
    const api: TurnReportResponse = {
      turn: 1,
      net_gold: 0,
      economy: [],
      battles: [],
      lines: [eventLine("event_neglected", "events.realm_in_turmoil.neglected", { stability: 64 })],
      major_event_kinds: ["event_neglected"],
    };
    const estimated = deriveTurnReport(null, DEFAULT_PREVIEW_WORLD, REGION_NAMES);
    const report = mergeTurnReport(estimated, api, DEFAULT_PREVIEW_WORLD, REGION_NAMES);
    expect(report.items.some((item) => item.title === "Neglected: The realm stirs")).toBe(true);
  });
});
