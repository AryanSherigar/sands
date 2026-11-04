import { LEVY_INFANTRY_PRESET } from "../constants/strategy.constants";
import type {
  AnnexVassalOrder,
  AppeaseCoalitionOrder,
  AppeaseOffer,
  ConsentActionKind,
  DemandFromVassalOrder,
  GrantConsentOrder,
  DemandTerm,
  DiplomaticPlayOrder,
  MobilizeOrder,
  SubsidizeOrder,
  VassalDemandKind,
  AnswerCallOrder,
  AnswerDemandOrder,
  AnswerEventOrder,
  AttackOrder,
  BesiegeOrder,
  CallNegotiationOrder,
  CutSubsidyOrder,
  DeclareDefaultOrder,
  DeclareWarOrder,
  DemandReply,
  DenounceAllianceOrder,
  DisbandArmyOrder,
  MergeArmiesOrder,
  SetArmyPolicyOrder,
  SplitArmyOrder,
  FabricateClaimOrder,
  HaltArmyOrder,
  HandlePrisonerOrder,
  MapScoutOrder,
  MediateOrder,
  MoveArmyOrder,
  PayLevel,
  PrisonerAction,
  RaiseArmyOrder,
  RegionView,
  ReleaseVassalOrder,
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

export function buildBesiegeOrder(
  factionId: string,
  armyId: string,
  targetRegionId: string,
): BesiegeOrder {
  return {
    kind: "besiege",
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

export function buildDisbandOrder(factionId: string, armyId: string): DisbandArmyOrder {
  return { kind: "disband_army", faction_id: factionId, army_id: armyId };
}

export function buildMergeOrder(
  factionId: string,
  armyIds: string[],
  intoArmyId: string,
): MergeArmiesOrder {
  return { kind: "merge_armies", faction_id: factionId, army_ids: armyIds, into_army_id: intoArmyId };
}

export function buildSplitOrder(
  factionId: string,
  armyId: string,
  troops: SplitArmyOrder["troops"],
): SplitArmyOrder {
  return { kind: "split_army", faction_id: factionId, army_id: armyId, troops };
}

export function buildArmyPolicyOrder(
  factionId: string,
  armyId: string,
  policy: Pick<SetArmyPolicyOrder, "withdrawal_policy" | "reserve_policy">,
): SetArmyPolicyOrder {
  return { kind: "set_army_policy", faction_id: factionId, army_id: armyId, ...policy };
}

export function buildMapScoutOrder(factionId: string, regionId: string): MapScoutOrder {
  return { kind: "map_scout", faction_id: factionId, target_region_id: regionId };
}

export function buildFabricateClaimOrder(
  factionId: string,
  targetFactionId: string,
  regionId: string,
): FabricateClaimOrder {
  return {
    kind: "fabricate_claim",
    faction_id: factionId,
    target_faction_id: targetFactionId,
    region_id: regionId,
  };
}

export function buildHandlePrisonerOrder(
  factionId: string,
  prisonerId: string,
  action: PrisonerAction,
): HandlePrisonerOrder {
  return { kind: "handle_prisoner", faction_id: factionId, prisoner_id: prisonerId, action };
}

export function buildMediateOrder(factionId: string, warId: string): MediateOrder {
  return { kind: "mediate", faction_id: factionId, war_id: warId };
}

export function buildCutSubsidyOrder(factionId: string, subsidyId: string): CutSubsidyOrder {
  return { kind: "cut_subsidy", faction_id: factionId, subsidy_id: subsidyId };
}

export function buildDenounceAllianceOrder(
  factionId: string,
  allianceId: string,
): DenounceAllianceOrder {
  return { kind: "denounce_alliance", faction_id: factionId, alliance_id: allianceId };
}

export function buildReleaseVassalOrder(
  factionId: string,
  vassalageId: string,
): ReleaseVassalOrder {
  return { kind: "release_vassal", faction_id: factionId, vassalage_id: vassalageId };
}

export function buildAnnexVassalOrder(factionId: string, vassalageId: string): AnnexVassalOrder {
  return { kind: "annex_vassal", faction_id: factionId, vassalage_id: vassalageId };
}

export function buildMobilizeOrder(factionId: string): MobilizeOrder {
  return { kind: "mobilize", faction_id: factionId };
}

export function buildSubsidizeOrder(
  factionId: string,
  targetFactionId: string,
  warId: string,
  amountPerTurn: number,
  turns: number,
): SubsidizeOrder {
  return {
    kind: "subsidize",
    faction_id: factionId,
    target_faction_id: targetFactionId,
    war_id: warId,
    amount_per_turn: amountPerTurn,
    turns,
  };
}

export function buildAppeaseOrder(
  factionId: string,
  memberId: string,
  offer: AppeaseOffer,
): AppeaseCoalitionOrder {
  return { kind: "appease_coalition", faction_id: factionId, member_id: memberId, offer };
}

export function buildGrantConsentOrder(
  factionId: string,
  vassalageId: string,
  action: ConsentActionKind,
  targetFactionId: string,
): GrantConsentOrder {
  return {
    kind: "grant_consent",
    faction_id: factionId,
    vassalage_id: vassalageId,
    action,
    target_faction_id: targetFactionId,
  };
}

export function buildVassalDemandOrder(
  factionId: string,
  vassalageId: string,
  demandKind: VassalDemandKind,
  amount: number,
): DemandFromVassalOrder {
  return {
    kind: "demand_from_vassal",
    faction_id: factionId,
    vassalage_id: vassalageId,
    demand_kind: demandKind,
    amount,
  };
}

export function buildDemandPlayOrder(
  factionId: string,
  targetFactionId: string,
  demands: DemandTerm[],
): DiplomaticPlayOrder {
  return { kind: "diplomatic_play", faction_id: factionId, target_faction_id: targetFactionId, demands };
}
