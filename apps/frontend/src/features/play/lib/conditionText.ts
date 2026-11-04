import type { ConditionTemplate } from "../types/scene.types";

type ConditionWords = { faction: string; value: number; region: string };

const CONDITION_TEXT: Record<ConditionTemplate, (words: ConditionWords) => string> = {
  treasury_below: ({ faction, value }) => `${faction}'s treasury falls below ${value}`,
  treasury_above: ({ faction, value }) => `${faction}'s treasury rises above ${value}`,
  stability_below: ({ faction, value }) => `${faction}'s stability falls below ${value}`,
  war_exhaustion_above: ({ faction, value }) => `${faction}'s war exhaustion rises above ${value}`,
  region_count_below: ({ faction, value }) => `${faction} holds fewer than ${value} regions`,
  region_count_above: ({ faction, value }) => `${faction} holds more than ${value} regions`,
  turn_after: ({ value }) => `turn ${value} has passed`,
  owns_region: ({ faction, region }) => `${faction} holds ${region}`,
  loses_region: ({ faction, region }) => `${faction} no longer holds ${region}`,
};

export const describeCondition = (
  template: ConditionTemplate,
  factionName: string,
  value: number,
  regionName = "a region",
): string => CONDITION_TEXT[template]({ faction: factionName, value, region: regionName });
