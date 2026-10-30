import { LEVY_INFANTRY_PRESET } from "../constants/strategy.constants";
import type {
  AnswerCallOrder,
  AnswerDemandOrder,
  AnswerEventOrder,
  AttackOrder,
  CallNegotiationOrder,
  DeclareDefaultOrder,
  DeclareWarOrder,
  DemandReply,
  HaltArmyOrder,
  MoveArmyOrder,
  PayLevel,
  RaiseArmyOrder,
  RegionView,
  ResolveUprisingOrder,
  SendEnvoyOrder,
  SetPayOrder,
  SetTaxRateOrder,
  SuePeaceOrder,
  TakeLoanOrder,
  TaxRate,
  UprisingResponseId,
} from "../types/simulation.types";
import type { SituationSource } from "../types/situation.types";

export function buildMoveOrder(
  factionId: string,
  armyId: string,
  toRegionId: string,
): MoveArmyOrder {
  return { kind: "move_army", faction_id: factionId, army_id: armyId, to_region_id: toRegionId };
}

export function buildAttackOrder(
  factionId: string,
  armyId: string,
  targetRegionId: string,
): AttackOrder {
  return {
    kind: "attack",
    faction_id: factionId,
    army_id: armyId,
    target_region_id: targetRegionId,
  };
}

export function buildHaltOrder(factionId: string, armyId: string): HaltArmyOrder {
  return { kind: "halt_army", faction_id: factionId, army_id: armyId };
}

export function buildLevyOrder(factionId: string, region: RegionView): RaiseArmyOrder {
  const availableManpower = region.detail?.manpower ?? LEVY_INFANTRY_PRESET;
  return {
    kind: "raise_army",
    faction_id: factionId,
    region_id: region.region_id,
    troops: { infantry: Math.min(LEVY_INFANTRY_PRESET, availableManpower) },
  };
}

export function buildAnswerEventOrder(
  factionId: string,
  eventId: string,
  choiceId: string,
): AnswerEventOrder {
  return { kind: "answer_event", faction_id: factionId, event_id: eventId, choice_id: choiceId };
}

export function buildResolveUprisingOrder(
  factionId: string,
  uprisingId: string,
  response: UprisingResponseId,
): ResolveUprisingOrder {
  return {
    kind: "resolve_uprising",
    faction_id: factionId,
    uprising_id: uprisingId,
    response,
  };
}

export function buildSituationAnswer(
  factionId: string,
  source: SituationSource | undefined,
  targetId: string,
  choiceId: string,
): AnswerEventOrder | ResolveUprisingOrder {
  if (source === "uprising") {
    return buildResolveUprisingOrder(factionId, targetId, choiceId as UprisingResponseId);
  }
  return buildAnswerEventOrder(factionId, targetId, choiceId);
}

export function buildSetTaxRateOrder(
  factionId: string,
  taxRate: TaxRate,
): SetTaxRateOrder {
  return { kind: "set_tax_rate", faction_id: factionId, tax_rate: taxRate };
}

export function buildTakeLoanOrder(
  factionId: string,
  amount: number,
): TakeLoanOrder {
  return { kind: "take_loan", faction_id: factionId, amount };
}

export function buildDeclareDefaultOrder(factionId: string): DeclareDefaultOrder {
  return { kind: "declare_default", faction_id: factionId };
}

export function buildSetPayOrder(
  factionId: string,
  armyId: string,
  payLevel: PayLevel,
): SetPayOrder {
  return {
    kind: "set_pay",
    faction_id: factionId,
    army_id: armyId,
    pay_level: payLevel,
  };
}

export function buildDeclareWarOrder(
  factionId: string,
  targetFactionId: string,
  groundId?: string | null,
): DeclareWarOrder {
  return {
    kind: "declare_war",
    faction_id: factionId,
    target_faction_id: targetFactionId,
    ground_id: groundId ?? null,
  };
}

export function buildSuePeaceOrder(factionId: string, warId: string): SuePeaceOrder {
  return { kind: "sue_peace", faction_id: factionId, war_id: warId };
}

export function buildCallNegotiationOrder(
  factionId: string,
  targetFactionId: string,
): CallNegotiationOrder {
  return { kind: "call_negotiation", faction_id: factionId, target_faction_id: targetFactionId };
}

export function buildSendEnvoyOrder(
  factionId: string,
  targetFactionId: string,
): SendEnvoyOrder {
  return { kind: "send_envoy", faction_id: factionId, target_faction_id: targetFactionId };
}

export function buildAnswerCallOrder(
  factionId: string,
  callId: string,
  isJoining: boolean,
): AnswerCallOrder {
  return {
    kind: "answer_call",
    faction_id: factionId,
    call_id: callId,
    is_joining: isJoining,
  };
}

export function buildAnswerDemandOrder(
  factionId: string,
  demandId: string,
  reply: DemandReply,
): AnswerDemandOrder {
  return {
    kind: "answer_demand",
    faction_id: factionId,
    demand_id: demandId,
    reply,
  };
}
