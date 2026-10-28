import type { StrategyAmbition } from "./StrategyRulerSetup.types";

export const BUILTIN_STRATEGY_AMBITIONS: readonly StrategyAmbition[] = [
  {
    id: "ambition_peace",
    name: "The Grand Truce Covenant",
    description: "Unite 3 factions in mutual defensive covenant without declaring an offensive war.",
    progress: 0,
  },
  {
    id: "ambition_granary",
    name: "The Great Granary",
    description: "Stockpile 1,000 bushels before Winter 1044 to permanently secure peasant loyalty.",
    progress: 34,
  },
  {
    id: "ambition_expand",
    name: "Imperial Unification",
    description: "Unite 4 frontier provinces under sovereign banner through conquest or diplomacy.",
    progress: 25,
  },
  {
    id: "ambition_wealth",
    name: "Golden Treasury",
    description: "Accumulate 500 gold in the royal vault while sustaining positive realm stability.",
    progress: 10,
  },
];
