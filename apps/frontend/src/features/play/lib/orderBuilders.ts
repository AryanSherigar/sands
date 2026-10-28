import { LEVY_INFANTRY_PRESET } from "../constants/strategy.constants";
import type {
  AnswerEventOrder,
  AttackOrder,
  HaltArmyOrder,
  MoveArmyOrder,
  RaiseArmyOrder,
  RegionView,
  ResolveUprisingOrder,
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
