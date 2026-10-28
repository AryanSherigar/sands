import { useMemo } from "react";
import {
  describeEffects,
  describeIntelligence,
  describeNeglect,
  memoryTitle,
  narrate,
  stageLabel,
  stageLabels,
  toStage,
} from "../lib/eventText";
import {
  UPRISING_MAX_STAGE,
  describeResponseEffects,
  describeUprisingCause,
  describeUprisingIntelligence,
  describeUprisingNeglect,
  responseLabel,
  uprisingStage,
  uprisingText,
} from "../lib/uprisingText";
import type {
  CampaignWorldView,
  EventMemoryView,
  PendingEventView,
  UprisingView,
} from "../types/simulation.types";
import type { ActiveSituation, SituationInterventionLever } from "../types/situation.types";

const ESCALATED_STAGE = 2;
const IF_IGNORED_PREFIX = "If unanswered by the next turn:";
const ONGOING_NOTE = "This trouble has not gone away and can flare up again if conditions worsen.";

type RegionNames = Record<string, string>;

export interface StrategySituations {
  situations: ActiveSituation[];
  activeCrisesCount: number;
  escalatedSituation: ActiveSituation | null;
}

function buildLevers(event: PendingEventView): SituationInterventionLever[] {
  return event.choices.map((choice) => ({
    id: `lever-${event.id}-${choice.id}`,
    label: choice.label_hint,
    orderCost: choice.order_cost,
    eventId: event.id,
    choiceId: choice.id,
    effects: describeEffects(choice.effects),
    isAffordable: choice.is_affordable,
    isQueued: event.queued_choice_id === choice.id,
    queuedCommandId: event.queued_choice_id === choice.id ? event.queued_command_id : null,
  }));
}

function regionLabel(regionId: string | null | undefined, fallback: string, names: RegionNames) {
  return regionId ? (names[regionId] ?? fallback) : fallback;
}

function eventSituation(event: PendingEventView, names: RegionNames): ActiveSituation {
  const narrative = narrate(event);
  const neglect = describeNeglect(event.neglect_effects);
  return {
    id: `situation-${event.id}`,
    eventId: event.id,
    title: narrative.title,
    regionId: event.region_id ?? null,
    regionName: regionLabel(event.region_id, event.subject_name, names),
    subheading: narrative.subheading,
    severityStage: toStage(event.tier),
    maxStage: toStage(event.max_tier),
    severityLabel: stageLabel(event.template_id, event.tier),
    stageLabels: stageLabels(event.template_id, event.max_tier),
    causeQuote: narrative.causeQuote,
    intelligence: describeIntelligence(event.cause_inputs),
    ifIgnoredWarning: neglect ? `${IF_IGNORED_PREFIX} ${neglect}.` : null,
    deadlineTurn: event.deadline_turn,
    scar: 0,
    isActionable: true,
    levers: buildLevers(event),
  };
}

function memorySituation(memory: EventMemoryView, names: RegionNames): ActiveSituation {
  return {
    id: `situation-memory-${memory.template_id}-${memory.subject_id}`,
    eventId: null,
    title: memoryTitle(memory),
    regionId: memory.region_id ?? null,
    regionName: regionLabel(memory.region_id, memory.subject_name, names),
    subheading: memory.name,
    severityStage: toStage(memory.last_tier),
    maxStage: toStage(memory.max_tier),
    severityLabel: stageLabel(memory.template_id, memory.last_tier),
    stageLabels: stageLabels(memory.template_id, memory.max_tier),
    causeQuote: ONGOING_NOTE,
    intelligence: memory.scar > 0 ? [`Lingering resentment: ${memory.scar}`] : [],
    ifIgnoredWarning: null,
    deadlineTurn: null,
    scar: memory.scar,
    isActionable: false,
    levers: [],
  };
}

function uprisingLevers(uprising: UprisingView): SituationInterventionLever[] {
  return uprising.responses.map((response) => ({
    source: "uprising",
    id: `lever-${uprising.id}-${response.id}`,
    label: responseLabel(response.id),
    orderCost: response.order_cost,
    eventId: uprising.id,
    choiceId: response.id,
    effects: describeResponseEffects(response),
    isAffordable: response.is_affordable,
    isQueued: uprising.queued_response === response.id,
    queuedCommandId: uprising.queued_response === response.id ? uprising.queued_command_id : null,
  }));
}

function uprisingSituation(uprising: UprisingView, names: RegionNames): ActiveSituation {
  const regionName = names[uprising.region_id] ?? uprising.region_id;
  const text = uprisingText(uprising.archetype);
  return {
    source: "uprising",
    id: `situation-${uprising.id}`,
    eventId: uprising.id,
    title: text.title(regionName),
    regionId: uprising.region_id,
    regionName,
    subheading: text.subheading,
    severityStage: uprisingStage(uprising.stage),
    maxStage: UPRISING_MAX_STAGE,
    severityLabel: text.stageLabels[uprisingStage(uprising.stage) - 1],
    stageLabels: text.stageLabels,
    causeQuote: describeUprisingCause(uprising, regionName),
    intelligence: describeUprisingIntelligence(uprising),
    ifIgnoredWarning: describeUprisingNeglect(uprising),
    deadlineTurn: null,
    scar: 0,
    isActionable: true,
    levers: uprisingLevers(uprising),
  };
}

function isStillPending(memory: EventMemoryView, events: PendingEventView[]): boolean {
  return events.some(
    (event) => event.template_id === memory.template_id && event.subject_id === memory.subject_id,
  );
}

export function useStrategySituations(
  world?: CampaignWorldView | null,
  regionNames: RegionNames = {},
): StrategySituations {
  return useMemo(() => {
    const events = world?.pending_events ?? [];
    const memories = world?.event_memories ?? [];
    const uprisings = (world?.uprisings ?? []).map((item) => uprisingSituation(item, regionNames));
    const pending = [...events.map((event) => eventSituation(event, regionNames)), ...uprisings];
    const ongoing = memories
      .filter((memory) => memory.last_tier > 0 && !isStillPending(memory, events))
      .map((memory) => memorySituation(memory, regionNames));
    const situations = [...pending, ...ongoing];
    const escalated = pending
      .filter((item) => item.severityStage >= ESCALATED_STAGE)
      .sort((left, right) => right.severityStage - left.severityStage)[0];
    return {
      situations,
      activeCrisesCount: situations.length,
      escalatedSituation: escalated ?? null,
    };
  }, [world, regionNames]);
}

