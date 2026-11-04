import type { CampaignWorldView, RivalView, StrategyOrder } from "../types/simulation.types";
import { describeCondition } from "./conditionText";
import {
  buildAnnexVassalOrder,
  buildCutSubsidyOrder,
  buildDenounceAllianceOrder,
  buildHandlePrisonerOrder,
  buildMediateOrder,
  buildMobilizeOrder,
  buildReleaseVassalOrder,
} from "./orderBuilders";

export interface RealmAffairConfirmation {
  title: string;
  message: string;
  confirmLabel: string;
}

export interface FormOption {
  id: string;
  label: string;
}

export type RealmAffairForm =
  | { kind: "subsidize"; warId: string; receivers: FormOption[] }
  | {
      kind: "appease";
      members: FormOption[];
      claimedRegionsByMember: Record<string, FormOption[]>;
    }
  | { kind: "vassal_demand"; vassalageId: string; tributePercent: number; levyPercent: number }
  | { kind: "grant_consent"; vassalageId: string; targets: FormOption[] };

export interface RealmAffairAction {
  label: string;
  order?: StrategyOrder;
  form?: RealmAffairForm;
  confirmation?: RealmAffairConfirmation;
}

export interface RealmAffair {
  id: string;
  title: string;
  detail: string;
  actions: RealmAffairAction[];
}

export interface RealmAffairGroup {
  id: string;
  heading: string;
  affairs: RealmAffair[];
}

type AffairWorld = Pick<
  CampaignWorldView,
  | "my_faction"
  | "rivals"
  | "alliances"
  | "sworn_promises"
  | "covenants"
  | "sworn_promise_history"
  | "conditional_clauses"
  | "vassalages"
  | "coalitions"
  | "wars"
  | "own_prisoners"
  | "own_hostages"
  | "open_mediations"
  | "subsidies"
  | "mobilization"
  | "regions"
  | "own_pressure"
>;

const nameOf = (rivals: RivalView[], factionId: string, myFactionId: string): string => {
  if (factionId === myFactionId) return "you";
  return rivals.find((rival) => rival.faction_id === factionId)?.name ?? factionId;
};

const untilTurn = (turn: number | undefined | null): string =>
  turn === undefined || turn === null ? "no fixed end" : `until turn ${turn}`;

function buildAlliances(world: AffairWorld): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.alliances ?? []).map((alliance) => ({
    id: alliance.id,
    title: `Allied with ${nameOf(world.rivals, alliance.partner_id, myId)}`,
    detail: [
      `${alliance.alliance_type} alliance, ${untilTurn(alliance.ends_turn)}`,
      alliance.is_separate_peace_banned ? "separate peace forbidden" : null,
    ]
      .filter(Boolean)
      .join("; "),
    actions: [
      {
        label: "Denounce",
        order: buildDenounceAllianceOrder(myId, alliance.id),
        confirmation: {
          title: "Denounce this alliance?",
          message: "The alliance ends. This cannot be undone.",
          confirmLabel: "Denounce",
        },
      },
    ],
  }));
}

function consentTargets(world: AffairWorld, myId: string, vassalId: string): FormOption[] {
  return world.rivals
    .filter((rival) => rival.faction_id !== myId && rival.faction_id !== vassalId)
    .map((rival) => ({ id: rival.faction_id, label: rival.name }));
}

function buildVassalages(world: AffairWorld): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.vassalages ?? []).map((vassalage) => {
    const isOverlord = vassalage.overlord_id === myId;
    const otherId = isOverlord ? vassalage.vassal_id : vassalage.overlord_id;
    const terms = `tribute ${vassalage.tribute_share_percent}%, levy ${vassalage.levy_share_percent}%, ${untilTurn(vassalage.ends_turn)}`;
    return {
      id: vassalage.id,
      title: isOverlord
        ? `${nameOf(world.rivals, otherId, myId)} serves you`
        : `You serve ${nameOf(world.rivals, otherId, myId)}`,
      detail: terms,
      actions: isOverlord
        ? [
            {
              label: "Make a demand",
              form: {
                kind: "vassal_demand",
                vassalageId: vassalage.id,
                tributePercent: vassalage.tribute_share_percent,
                levyPercent: vassalage.levy_share_percent,
              },
            },
            {
              label: "Grant consent",
              form: {
                kind: "grant_consent",
                vassalageId: vassalage.id,
                targets: consentTargets(world, myId, vassalage.vassal_id),
              },
            },
            {
              label: "Release",
              order: buildReleaseVassalOrder(myId, vassalage.id),
              confirmation: {
                title: "Release this vassal?",
                message: "They become independent again.",
                confirmLabel: "Release",
              },
            },
            {
              label: "Annex",
              order: buildAnnexVassalOrder(myId, vassalage.id),
              confirmation: {
                title: "Annex this vassal?",
                message: "Their lands are absorbed into your realm. This cannot be undone.",
                confirmLabel: "Annex",
              },
            },
          ]
        : [],
    };
  });
}

const PROMISE_TEXT: Record<string, string> = {
  never_attack_faction: "never to attack",
  never_ally_with: "never to ally with",
  spare_prisoners: "to spare prisoners",
  never_occupy_region: "never to occupy",
};

const subjectName = (world: AffairWorld, subjectId: string, regionNames: RegionNames): string =>
  regionNames[subjectId] ?? nameOf(world.rivals, subjectId, world.my_faction.id);

function buildOaths(world: AffairWorld, regionNames: RegionNames): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.sworn_promises ?? []).map((oath) => {
    const isMine = oath.promisor_id === myId;
    const other = nameOf(world.rivals, isMine ? oath.beneficiary_id : oath.promisor_id, myId);
    const subject = oath.subject_id ? ` ${subjectName(world, oath.subject_id, regionNames)}` : "";
    const promiseText = PROMISE_TEXT[oath.promise] ?? oath.promise;
    return {
      id: oath.commitment_id,
      title: isMine ? `You swore to ${other} ${promiseText}${subject}` : `${other} swore to you ${promiseText}${subject}`,
      detail: `In force ${untilTurn(oath.end_turn)}`,
      actions: [],
    };
  });
}

const COVENANT_TEXT: Record<string, string> = {
  tax_relief: "to keep taxes low",
  garrison_out: "to keep soldiers out",
  amnesty: "not to crack down on the rebels",
  relief_small: "a small relief",
  relief_large: "a great relief",
};

function buildCovenants(world: AffairWorld, regionNames: RegionNames): RealmAffair[] {
  return (world.covenants ?? []).map((covenant) => ({
    id: covenant.covenant_id,
    title: `You swore the people of ${regionNames[covenant.region_id] ?? covenant.region_id} ${COVENANT_TEXT[covenant.covenant] ?? covenant.covenant}`,
    detail: `Breaking it rekindles the revolt. In force ${untilTurn(covenant.end_turn)}`,
    actions: [],
  }));
}

const CLAUSE_STATE_TEXT: Record<string, string> = {
  pending: "Waiting for the condition to hold",
  gate_open: "Gate open: the clause is in force",
  gate_closed: "Gate closed: the clause is suspended",
};

function buildConditionalClauses(world: AffairWorld, regionNames: RegionNames): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.conditional_clauses ?? []).map((clause) => {
    const condition = describeCondition(
      clause.template,
      nameOf(world.rivals, clause.condition_faction_id, myId),
      clause.condition_value,
      regionNames[clause.condition_region_id ?? ""] ?? clause.condition_region_id ?? undefined,
    );
    const parties = clause.party_ids.map((id) => nameOf(world.rivals, id, myId)).join(" and ");
    const kind = clause.inner_kind.replace(/_/g, " ");
    return {
      id: clause.commitment_id,
      title: `If ${condition}: ${kind} between ${parties}`,
      detail: `${CLAUSE_STATE_TEXT[clause.state]}. Runs ${untilTurn(clause.end_turn)}`,
      actions: [],
    };
  });
}

type RegionNames = Record<string, string>;

function appeaseAction(
  world: AffairWorld,
  coalition: NonNullable<AffairWorld["coalitions"]>[number],
  regionNames: RegionNames,
): RealmAffairAction {
  const myId = world.my_faction.id;
  const claimedRegionsByMember: Record<string, FormOption[]> = {};
  for (const memberId of coalition.member_ids) {
    claimedRegionsByMember[memberId] = (world.regions ?? [])
      .filter((region) => region.owner_id === myId && region.detail?.claimant_ids?.includes(memberId))
      .map((region) => ({ id: region.region_id, label: regionNames[region.region_id] ?? region.region_id }));
  }
  return {
    label: "Appease a member",
    form: {
      kind: "appease",
      members: coalition.member_ids.map((id) => ({ id, label: nameOf(world.rivals, id, myId) })),
      claimedRegionsByMember,
    },
  };
}

const OUTCOME_TEXT: Record<string, string> = {
  breached: "Broken",
  fulfilled: "Kept to the end",
  expired: "Lapsed",
};

function buildOathHistory(world: AffairWorld, regionNames: RegionNames): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.sworn_promise_history ?? []).map((oath) => {
    const isMine = oath.promisor_id === myId;
    const other = nameOf(world.rivals, isMine ? oath.beneficiary_id : oath.promisor_id, myId);
    const subject = oath.subject_id ? ` ${subjectName(world, oath.subject_id, regionNames)}` : "";
    const promiseText = PROMISE_TEXT[oath.promise] ?? oath.promise;
    return {
      id: `history-${oath.commitment_id}`,
      title: isMine ? `You swore to ${other} ${promiseText}${subject}` : `${other} swore to you ${promiseText}${subject}`,
      detail: OUTCOME_TEXT[oath.outcome] ?? oath.outcome,
      actions: [],
    };
  });
}

function buildCoalitions(world: AffairWorld, regionNames: RegionNames): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.coalitions ?? []).map((coalition) => ({
    id: coalition.id,
    title: `Coalition against ${nameOf(world.rivals, coalition.target_id, myId)}`,
    detail: `${coalition.member_ids.map((id) => nameOf(world.rivals, id, myId)).join(", ")}; expires turn ${coalition.expires_turn}`,
    actions: coalition.target_id === myId ? [appeaseAction(world, coalition, regionNames)] : [],
  }));
}

const OUTLOOK_TEXT: Record<string, string> = {
  leading: "you are winning",
  even: "the war is evenly matched",
  trailing: "you are losing",
};

function describeWar(war: NonNullable<AffairWorld["wars"]>[number]): string {
  const outlook = war.outlook ? OUTLOOK_TEXT[war.outlook] : null;
  const slots = war.goal_slots ? `${war.goal_slots} war ${war.goal_slots === 1 ? "goal" : "goals"} to claim` : null;
  return [`War #${war.id}`, outlook, slots].filter(Boolean).join("; ");
}

function buildWars(world: AffairWorld): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.wars ?? []).map((war) => {
    const isMine = war.attacker_id === myId || war.defender_id === myId;
    const sides = `${nameOf(world.rivals, war.attacker_id, myId)} against ${nameOf(world.rivals, war.defender_id, myId)}`;
    return {
      id: war.id,
      title: isMine ? `Your war: ${sides}` : `War: ${sides}`,
      detail: describeWar(war),
      actions: isMine ? [] : [
        { label: "Offer mediation", order: buildMediateOrder(myId, war.id) },
        {
          label: "Subsidize a side",
          form: {
            kind: "subsidize",
            warId: war.id,
            receivers: [war.attacker_id, war.defender_id].map((id) => ({ id, label: nameOf(world.rivals, id, myId) })),
          },
        },
      ],
    };
  });
}

function buildPrisoners(world: AffairWorld): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.own_prisoners ?? []).map((prisoner) => ({
    id: prisoner.id,
    title: `${prisoner.name}, ${prisoner.title}`,
    detail: `Of ${nameOf(world.rivals, prisoner.origin_faction_id, myId)}; ransom ${prisoner.ransom_value_gold}g`,
    actions: [
      { label: "Ransom", order: buildHandlePrisonerOrder(myId, prisoner.id, "ransom") },
      { label: "Exchange", order: buildHandlePrisonerOrder(myId, prisoner.id, "exchange") },
      { label: "Release", order: buildHandlePrisonerOrder(myId, prisoner.id, "release") },
      {
        label: "Execute",
        order: buildHandlePrisonerOrder(myId, prisoner.id, "execute"),
        confirmation: {
          title: "Execute this prisoner?",
          message: "This cannot be undone and rival courts will remember it.",
          confirmLabel: "Execute",
        },
      },
    ],
  }));
}

function buildSubsidies(world: AffairWorld): RealmAffair[] {
  const myId = world.my_faction.id;
  return (world.subsidies ?? []).map((subsidy) => {
    const isPayer = subsidy.payer_id === myId;
    const counterpart = nameOf(world.rivals, isPayer ? subsidy.receiver_id : subsidy.payer_id, myId);
    return {
      id: subsidy.id,
      title: isPayer ? `You pay ${counterpart}` : `${counterpart} pays you`,
      detail: `${subsidy.amount_per_turn}g a turn, ${subsidy.turns_left} turns left (War #${subsidy.war_id})`,
      actions: isPayer
        ? [{ label: "Cut subsidy", order: buildCutSubsidyOrder(myId, subsidy.id) }]
        : [],
    };
  });
}

function buildHostagesAndMobilization(world: AffairWorld): RealmAffair[] {
  const myId = world.my_faction.id;
  const hostages = (world.own_hostages ?? []).map((hostage) => ({
    id: hostage.id,
    title: `Hostage held by ${nameOf(world.rivals, hostage.holder_id, myId)}`,
    detail: `Released on turn ${hostage.release_turn}${hostage.is_at_mercy ? "; at their mercy" : ""}`,
    actions: [],
  }));
  return [...hostages, ...buildMobilization(world)];
}

function buildMobilization(world: AffairWorld): RealmAffair[] {
  const myId = world.my_faction.id;
  if (world.mobilization) {
    return [{ id: "mobilization", title: "The realm is mobilized", detail: `${world.mobilization.turns_left} turns left`, actions: [] }];
  }
  const isAtWar = (world.wars ?? []).some((war) => war.attacker_id === myId || war.defender_id === myId);
  if (!isAtWar) return [];
  return [
    {
      id: "mobilize",
      title: "Mobilize the realm",
      detail: "Raise manpower and taxes for a time, at a cost to stability.",
      actions: [
        {
          label: "Mobilize",
          order: buildMobilizeOrder(myId),
          confirmation: {
            title: "Mobilize the realm?",
            message:
              "Manpower refills faster, taxes rise and you gain orders for a time. Stability falls, unrest and war exhaustion grow, and the strain of war rises.",
            confirmLabel: "Mobilize",
          },
        },
      ],
    },
  ];
}

function describeFactors(factors: Record<string, number> | undefined): string {
  if (!factors) return "none";
  const active = Object.entries(factors)
    .filter(([, val]) => val > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([key]) => key.replace(/_/g, " "));
  return active.length > 0 ? active.join(", ") : "none";
}

function buildWarPressure(world: AffairWorld): RealmAffair[] {
  if (!world.own_pressure) return [];
  const strainWord = world.own_pressure.strain_band.replace(/_/g, " ");
  const willWord = world.own_pressure.will_band.replace(/_/g, " ");
  const strainSources = describeFactors(world.own_pressure.strain_factors);
  const willSources = describeFactors(world.own_pressure.will_factors);
  return [
    {
      id: "own-war-pressure",
      title: `Strain: ${strainWord} · Resolve: ${willWord}`,
      detail: `Strain from ${strainSources}; resolve from ${willSources}.`,
      actions: [],
    },
  ];
}

export function buildRealmAffairGroups(world: AffairWorld, regionNames: RegionNames = {}): RealmAffairGroup[] {
  const groups: RealmAffairGroup[] = [
    { id: "war-pressure", heading: "War pressure", affairs: buildWarPressure(world) },
    { id: "wars", heading: "Wars", affairs: buildWars(world) },
    { id: "alliances", heading: "Alliances", affairs: buildAlliances(world) },
    { id: "oaths", heading: "Sworn oaths", affairs: buildOaths(world, regionNames) },
    { id: "covenants", heading: "Covenants with the people", affairs: buildCovenants(world, regionNames) },
    { id: "oath-history", heading: "Oaths of the past", affairs: buildOathHistory(world, regionNames) },
    { id: "conditional-clauses", heading: "Conditional clauses", affairs: buildConditionalClauses(world, regionNames) },
    { id: "vassals", heading: "Overlords and vassals", affairs: buildVassalages(world) },
    { id: "coalitions", heading: "Coalitions", affairs: buildCoalitions(world, regionNames) },
    { id: "prisoners", heading: "Prisoners", affairs: buildPrisoners(world) },
    { id: "subsidies", heading: "War subsidies", affairs: buildSubsidies(world) },
    { id: "other", heading: "Hostages and mobilization", affairs: buildHostagesAndMobilization(world) },
  ];
  return groups.filter((group) => group.affairs.length > 0);
}
