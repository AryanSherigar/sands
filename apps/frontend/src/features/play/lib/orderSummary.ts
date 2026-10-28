import type { StrategyOrder } from "../types/simulation.types";
import { responseLabel } from "./uprisingText";

const toTitle = (value: string): string =>
  value.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());

export type RegionNameLookup = Record<string, string>;

export function describeOrder(order: StrategyOrder, regionNames: RegionNameLookup = {}): string {
  const nameOf = (regionId: string): string => regionNames[regionId] ?? toTitle(regionId);
  switch (order.kind) {
    case "answer_event":
      return `Answer: ${toTitle(order.choice_id)}`;
    case "resolve_uprising":
      return `Answer uprising: ${responseLabel(order.response)}`;
    case "move_army":
      return `March to ${nameOf(order.to_region_id)}`;
    case "halt_army":
      return "Halt army";
    case "attack":
      return `Attack ${nameOf(order.target_region_id)}`;
    case "raise_army":
      return `Levy troops in ${nameOf(order.region_id)}`;
    case "disband_army":
      return "Disband army";
    case "set_tax_rate":
      return `Set taxes to ${order.tax_rate}`;
    case "take_loan":
      return `Take loan of ${order.amount}g`;
    case "build_improvement":
      return `Build ${toTitle(order.improvement_kind)}`;
  }
}
