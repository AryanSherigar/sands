import type { ActiveSituation } from "../types/situation.types";
import type {
  AllianceView,
  CallView,
  CampaignWorldView,
  CoalitionView,
  EndingState,
  EventMemoryView,
  HostageView,
  MediationOfferView,
  MobilizationView,
  OwnThreatView,
  PendingBattle,
  PendingDemandView,
  PendingEventView,
  SubsidyView,
  TruceView,
  UprisingView,
  VassalageView,
} from "../types/simulation.types";
import { DEFAULT_PREVIEW_WORLD } from "../components/StrategyPlayScreen/defaultPreviewWorld";

export function makeCampaignWorld(
  overrides: Partial<CampaignWorldView> = {},
): CampaignWorldView {
  return {
    ...DEFAULT_PREVIEW_WORLD,
    ...overrides,
  };
}

export function makeAlliance(
  overrides: Partial<AllianceView> = {},
): AllianceView {
  return {
    id: "alliance_1",
    partner_id: "f-oakhaven",
    alliance_type: "defensive",
    ends_turn: 10,
    is_separate_peace_banned: true,
    ...overrides,
  };
}

export function makeVassalage(
  overrides: Partial<VassalageView> = {},
): VassalageView {
  return {
    id: "vassalage_1",
    overlord_id: "f-valenreach",
    vassal_id: "f-oakhaven",
    tribute_share_percent: 20,
    levy_share_percent: 15,
    is_foreign_policy_controlled: true,
    has_garrison_rights: true,
    ends_turn: 20,
    ...overrides,
  };
}

export function makeCoalition(
  overrides: Partial<CoalitionView> = {},
): CoalitionView {
  return {
    id: "coalition-1",
    target_id: "f-ironmark",
    member_ids: ["f-valenreach", "f-oakhaven"],
    expires_turn: 10,
    ...overrides,
  };
}

export function makeTruce(
  overrides: Partial<TruceView> = {},
): TruceView {
  return {
    faction_a: "f-valenreach",
    faction_b: "f-ironmark",
    tier: "short",
    expires_turn: 5,
    is_fragile: false,
    guarantor_ids: [],
    ...overrides,
  };
}

export function makeHostage(
  overrides: Partial<HostageView> = {},
): HostageView {
  return {
    id: "hostage_1",
    giver_id: "f-ironmark",
    holder_id: "f-valenreach",
    leader_id: "ldr-brandon",
    release_turn: 8,
    is_at_mercy: false,
    ...overrides,
  };
}

export function makeCall(
  overrides: Partial<CallView> = {},
): CallView {
  return {
    id: "call_1",
    caller_id: "f-oakhaven",
    war_id: "war_1",
    side: "defender",
    is_defensive: true,
    deadline_turn: 3,
    ...overrides,
  };
}

export function makePendingDemand(
  overrides: Partial<PendingDemandView> = {},
): PendingDemandView {
  return {
    id: "demand_1",
    overlord_id: "f-ironmark",
    kind: "gold",
    amount: 50,
    granted: 0,
    deadline_turn: 4,
    ...overrides,
  };
}

export function makeOwnThreat(
  overrides: Partial<OwnThreatView> = {},
): OwnThreatView {
  return {
    band: "elevated",
    factors: { aggression: 30, border_friction: 15 },
    ...overrides,
  };
}

export function makeMediationOffer(
  overrides: Partial<MediationOfferView> = {},
): MediationOfferView {
  return {
    id: "med_1",
    mediator_id: "f-highcrag",
    war_id: "war_1",
    expires_turn: 5,
    ...overrides,
  };
}

export function makeSubsidy(
  overrides: Partial<SubsidyView> = {},
): SubsidyView {
  return {
    id: "sub_1",
    payer_id: "f-valenreach",
    receiver_id: "f-oakhaven",
    war_id: "war_1",
    amount_per_turn: 25,
    turns_left: 4,
    ...overrides,
  };
}

export function makeMobilization(
  overrides: Partial<MobilizationView> = {},
): MobilizationView {
  return {
    turns_left: 3,
    ...overrides,
  };
}

export function makePendingBattle(
  overrides: Partial<PendingBattle> = {},
): PendingBattle {
  return {
    battle_id: "battle_1",
    region_id: "reg-dunmere",
    attacker_faction_id: "f-ironmark",
    defender_faction_id: "f-valenreach",
    ...overrides,
  };
}

export function makeEndingState(
  overrides: Partial<EndingState> = {},
): EndingState {
  return {
    ending_id: "ending_1",
    kind: "victory",
    turn: 10,
    grade: "triumph",
    ...overrides,
  };
}

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
