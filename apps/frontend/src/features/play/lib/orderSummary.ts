import type { QueuedOrderView, StrategyOrder } from "../types/simulation.types";
import { responseLabel } from "./uprisingText";

const toTitle = (value: string): string =>
  value.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());

export type RegionNameLookup = Record<string, string>;
export type FactionNameLookup = Record<string, string>;

const resolveRegionName = (id: string, lookup: RegionNameLookup): string =>
  lookup[id] ?? toTitle(id);

const resolveFactionName = (id: string, lookup: FactionNameLookup): string =>
  lookup[id] ?? toTitle(id);

export function describeOrder(
  target: StrategyOrder | QueuedOrderView,
  regionNames: RegionNameLookup = {},
  factionNames: FactionNameLookup = {},
): string {
  const order = "kind" in target ? target : target.order;
  switch (order.kind) {
    case "declare_war":
      return `Declare war on ${resolveFactionName(order.target_faction_id, factionNames)}`;
    case "sue_peace":
      return `Sue for peace (War #${order.war_id})`;
    case "call_negotiation":
      return `Summon talks with ${resolveFactionName(order.target_faction_id, factionNames)}`;
    case "send_envoy":
      return `Dispatch envoy to ${resolveFactionName(order.target_faction_id, factionNames)}`;
    case "answer_call":
      return order.is_joining ? "Honour war call" : "Refuse war call";
    case "answer_demand":
      return `Answer demand: ${order.reply}`;
    case "answer_event":
      return `Answer: ${toTitle(order.choice_id)}`;
    case "resolve_uprising":
      return `Answer uprising: ${responseLabel(order.response)}`;
    case "move_army":
      return `March to ${resolveRegionName(order.to_region_id, regionNames)}`;
    case "halt_army":
      return "Halt army";
    case "attack":
      return `Attack ${resolveRegionName(order.target_region_id, regionNames)}`;
    case "besiege":
      return `Besiege ${resolveRegionName(order.target_region_id, regionNames)}`;
    case "raise_army":
      return `Levy troops in ${resolveRegionName(order.region_id, regionNames)}`;
    case "disband_army":
      return "Disband army";
    case "map_scout":
      return `Scout ${resolveRegionName(order.target_region_id, regionNames)}`;
    case "fabricate_claim":
      return `Fabricate a claim on ${resolveRegionName(order.region_id, regionNames)}`;
    case "handle_prisoner":
      return `${toTitle(order.action)} a prisoner`;
    case "mediate":
      return `Mediate (War #${order.war_id})`;
    case "cut_subsidy":
      return "Cut a war subsidy";
    case "denounce_alliance":
      return "Denounce an alliance";
    case "release_vassal":
      return "Release a vassal";
    case "annex_vassal":
      return "Annex a vassal";
    case "mobilize":
      return "Mobilize the realm";
    case "subsidize":
      return `Subsidize ${resolveFactionName(order.target_faction_id, factionNames)} (${order.amount_per_turn}g for ${order.turns} turns)`;
    case "appease_coalition":
      return `Appease ${resolveFactionName(order.member_id, factionNames)}`;
    case "demand_from_vassal":
      return `Demand ${order.demand_kind} from a vassal`;
    case "diplomatic_play":
      return `Make demands of ${resolveFactionName(order.target_faction_id, factionNames)}`;
    case "set_tax_rate":
      return `Set taxes to ${order.tax_rate}`;
    case "take_loan":
      return `Take loan of ${order.amount}g`;
    case "set_pay":
      return `Set pay to ${order.pay_level}`;
    case "declare_default":
      return "Declare sovereign default";
    case "build_improvement":
      return `Build ${toTitle(order.improvement_kind)}`;
  }
}
