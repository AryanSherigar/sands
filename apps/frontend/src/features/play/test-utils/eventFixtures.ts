import type { ActiveSituation } from "../types/situation.types";
import type {
  EventMemoryView,
  PendingEventView,
  UprisingView,
} from "../types/simulation.types";

export function makePendingEvent(overrides: Partial<PendingEventView> = {}): PendingEventView {
  return {
    id: "event_1",
    template_id: "tax_grievance",
    name: "Tax grievance",
    subject_kind: "region",
    subject_id: "ashford",
    subject_name: "Ashford Vale",
    region_id: "ashford",
    tier: 2,
    max_tier: 3,
    created_turn: 4,
    deadline_turn: 5,
    cause_key: "tax_grievance",
    cause_inputs: { region_unrest: 62, governor_opinion: -40 },
    choices: [
      {
        id: "ease_taxes",
        label_hint: "Lighten the levy in this region",
        order_cost: 1,
        effects: [
          { kind: "region_unrest", amount: -10 },
          { kind: "gold", amount: -20 },
        ],
        is_affordable: true,
      },
      {
        id: "garrison_crackdown",
        label_hint: "Send troops to break the protest",
        order_cost: 2,
        effects: [
          { kind: "region_unrest", amount: -15 },
          { kind: "governor_opinion", amount: -10 },
        ],
        is_affordable: true,
      },
    ],
    neglect_effects: [
      { kind: "region_unrest", amount: 10 },
      { kind: "governor_opinion", amount: -10 },
    ],
    queued_choice_id: null,
    queued_command_id: null,
    ...overrides,
  };
}

export function makeEventMemory(overrides: Partial<EventMemoryView> = {}): EventMemoryView {
  return {
    template_id: "tax_grievance",
    name: "Tax grievance",
    subject_id: "ashford",
    subject_name: "Ashford Vale",
    region_id: "ashford",
    last_tier: 1,
    max_tier: 3,
    scar: 0,
    ...overrides,
  };
}

export function makeSituation(overrides: Partial<ActiveSituation> = {}): ActiveSituation {
  return {
    id: "situation-event_1",
    eventId: "event_1",
    title: "Grievance in Ashford Vale",
    regionId: "ashford",
    regionName: "Ashford Vale",
    subheading: "Provincial Domain",
    severityStage: 2,
    maxStage: 3,
    severityLabel: "Petition",
    stageLabels: ["Murmurs", "Petition", "Revolt looms"],
    causeQuote: "Because unrest is 62 and the governor's opinion of you is −40.",
    intelligence: ["Unrest is 62"],
    ifIgnoredWarning: "If unanswered by the next turn: Unrest +10.",
    deadlineTurn: 5,
    scar: 0,
    isActionable: true,
    levers: [
      {
        id: "lever-event_1-ease_taxes",
        label: "Lighten the levy in this region",
        orderCost: 1,
        eventId: "event_1",
        choiceId: "ease_taxes",
        effects: ["Unrest −10"],
        isAffordable: true,
        isQueued: false,
        queuedCommandId: null,
      },
    ],
    ...overrides,
  };
}

export function makeUprising(overrides: Partial<UprisingView> = {}): UprisingView {
  return {
    id: "uprising_ashford_4",
    region_id: "ashford",
    faction_id: "house_carrow",
    started_turn: 4,
    trigger_unrest: 78,
    income_penalty_percent: 50,
    manpower_penalty_percent: 50,
    supply_penalty_percent: 50,
    archetype: "petition",
    stage: "unrest",
    turns_in_stage: 1,
    easing_turns: 0,
    responses: [
      {
        id: "concessions",
        order_cost: 1,
        effects: [
          { kind: "region_unrest", amount: -30 },
          { kind: "reputation", amount: -5 },
        ],
        notes: ["Other restless provinces grow bolder (+5 unrest)."],
        is_affordable: true,
      },
      {
        id: "restore_order",
        order_cost: 1,
        effects: [{ kind: "region_unrest", amount: -15 }],
        notes: [],
        is_affordable: true,
      },
    ],
    turns_until_change: 2,
    is_final_stage: false,
    is_easing: false,
    rebel_troops: null,
    queued_response: null,
    queued_command_id: null,
    ...overrides,
  };
}
