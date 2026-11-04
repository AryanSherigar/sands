import { describeCause, eventTitle } from "./eventText";
import { getEndingTitle } from "../components/StrategyPlayScreen/ending/strategyEnding.constants";
import type { ReportItem } from "../types/turnReport.types";
import type { ApiReportLine } from "../types/turnReportApi.types";

const EVENT_KINDS = new Set(["event_fired", "event_answered", "event_neglected"]);
const ENDING_KIND = "ending_reached";
const ENDING_PREFIX = "endings.";
const SUMMARY_PREFIX = "events.";
const NEGLECTED_SUFFIX = "neglected";

type RegionNames = Record<string, string>;

const toTitle = (value: string): string =>
  value.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());

interface ParsedEventLine {
  templateId: string;
  choiceId: string | null;
}

function parseSummaryKey(summaryKey: string): ParsedEventLine {
  const [templateId, tail] = summaryKey.slice(SUMMARY_PREFIX.length).split(".");
  const isNeglect = tail === NEGLECTED_SUFFIX;
  return { templateId, choiceId: tail && !isNeglect ? tail : null };
}

function cardFor(
  line: ApiReportLine,
  subject: string,
  parsed: ParsedEventLine,
): Pick<ReportItem, "title" | "description" | "badge"> {
  const title = eventTitle(parsed.templateId, subject);
  const cause = describeCause(line.cause?.inputs ?? {});
  if (line.kind === "event_answered") {
    const choice = parsed.choiceId ? toTitle(parsed.choiceId) : "Answered";
    return {
      title: `Answered: ${title}`,
      description: `${choice}. ${cause}`.trim(),
      badge: { label: choice, tone: "positive" },
    };
  }
  if (line.kind === "event_neglected") {
    return {
      title: `Neglected: ${title}`,
      description: `Left unanswered, so the situation worsened. ${cause}`.trim(),
      badge: { label: "Neglected", tone: "danger" },
    };
  }
  return {
    title: `Trouble: ${title}`,
    description: cause || "A matter now needs your decision.",
    badge: { label: "Needs a decision", tone: "warning" },
  };
}

function isEndingLine(line: ApiReportLine): boolean {
  return line.kind === ENDING_KIND && line.text_key.startsWith(ENDING_PREFIX);
}

function toEndingReportItem(line: ApiReportLine, index: number): ReportItem {
  return {
    id: `ending-${index}`,
    category: "internal",
    title: getEndingTitle(line.text_key.slice(ENDING_PREFIX.length)),
    description: "The reign has ended.",
    badge: { label: "Reign ended", tone: "neutral" },
  };
}

export function isEventLine(line: ApiReportLine): boolean {
  if (isEndingLine(line)) return true;
  return EVENT_KINDS.has(line.kind) && line.text_key.startsWith(SUMMARY_PREFIX);
}

export function toEventReportItem(
  line: ApiReportLine,
  index: number,
  regionNames: RegionNames,
): ReportItem {
  if (isEndingLine(line)) return toEndingReportItem(line, index);
  const parsed = parseSummaryKey(line.text_key);
  const subjectId = line.subject_ids[0] ?? "";
  const subject = regionNames[subjectId] ?? toTitle(subjectId);
  return {
    id: `event-${line.kind}-${subjectId}-${index}`,
    category: "internal",
    regionId: regionNames[subjectId] ? subjectId : undefined,
    ...cardFor(line, subject, parsed),
  };
}
