import type { StrategyTrait } from "./StrategyRulerSetup.types";

export const BUILTIN_STRATEGY_TRAITS: readonly StrategyTrait[] = [
  {
    id: "disciplined_steward",
    name: "Disciplined Steward",
    description: "Rigorous oversight of the grain ledgers and manor taxes.",
    effects: [
      { label: "+15% Tax Eff.", isPositive: true },
      { label: "+1 Stability", isPositive: true },
    ],
  },
  {
    id: "covenant_keeper",
    name: "Covenant Keeper",
    description: "Holds diplomatic treaties as sacred seals of blood.",
    effects: [
      { label: "+20 Diplo Trust", isPositive: true },
      { label: "2x Treaty Penalty", isPositive: false },
    ],
  },
  {
    id: "cautious_tactician",
    name: "Cautious Tactician",
    description: "Never commits reserves until defensive lines hold fast.",
    effects: [
      { label: "+25% Home Def", isPositive: true },
      { label: "-10% Cav Charge", isPositive: false },
    ],
  },
  {
    id: "honorable",
    name: "Honorable",
    description: "Keeps their word and expects the same; scorns tricks.",
    effects: [
      { label: "+30 Honor", isPositive: true },
      { label: "-1 Cunning", isPositive: false },
    ],
  },
  {
    id: "cautious",
    name: "Cautious",
    description: "Weighs every risk and prefers safe, lasting arrangements.",
    effects: [
      { label: "+20% Defense", isPositive: true },
      { label: "-10% Aggression", isPositive: false },
    ],
  },
  {
    id: "treacherous",
    name: "Treacherous",
    description: "Treats promises as tools and assumes others do too.",
    effects: [
      { label: "+25 Cunning", isPositive: true },
      { label: "-30 Diplo Trust", isPositive: false },
    ],
  },
  {
    id: "proud",
    name: "Proud",
    description: "Hears weakness in any request and is slow to concede.",
    effects: [
      { label: "+20 Pride", isPositive: true },
      { label: "-10 Caution", isPositive: false },
    ],
  },
  {
    id: "wrathful",
    name: "Wrathful",
    description: "Quick to anger and eager for a fight.",
    effects: [
      { label: "+25% Attack", isPositive: true },
      { label: "-15 Caution", isPositive: false },
    ],
  },
  {
    id: "pragmatic",
    name: "Pragmatic",
    description: "Judges an offer by its worth, not its pride.",
    effects: [
      { label: "+15% Trade Eff.", isPositive: true },
      { label: "-10 Zeal", isPositive: false },
    ],
  },
  {
    id: "cunning",
    name: "Cunning",
    description: "Looks for the hidden angle and distrusts easy offers.",
    effects: [
      { label: "+20 Espionage", isPositive: true },
      { label: "-15 Trust", isPositive: false },
    ],
  },
  {
    id: "paranoid",
    name: "Paranoid",
    description: "Expects betrayal and wants guarantees.",
    effects: [
      { label: "+25 Anti-Spy", isPositive: true },
      { label: "-20 Diplo Trust", isPositive: false },
    ],
  },
  {
    id: "trusting",
    name: "Trusting",
    description: "Takes people at their word and warms to goodwill.",
    effects: [
      { label: "+25 Diplo Trust", isPositive: true },
      { label: "-20 Espionage Def", isPositive: false },
    ],
  },
  {
    id: "naive",
    name: "Naive",
    description: "Believes fair-sounding offers and misses the trap.",
    effects: [
      { label: "+15 Diplo Trust", isPositive: true },
      { label: "-25 Counter-Intel", isPositive: false },
    ],
  },
  {
    id: "stubborn",
    name: "Stubborn",
    description: "Digs in once a position is taken.",
    effects: [
      { label: "+20 Siege Def", isPositive: true },
      { label: "-15 Treaty Flex", isPositive: false },
    ],
  },
  {
    id: "calculating",
    name: "Calculating",
    description: "Bargains coldly and keeps count of every concession.",
    effects: [
      { label: "+15% Concession Value", isPositive: true },
      { label: "-10 Opinion", isPositive: false },
    ],
  },
  {
    id: "cruel",
    name: "Cruel",
    description: "Has little pity and respects only strength.",
    effects: [
      { label: "+20 Intimidation", isPositive: true },
      { label: "-20 Honor", isPositive: false },
    ],
  },
  {
    id: "zealot",
    name: "Zealot",
    description: "Sees the world through faith and distrusts unbelievers.",
    effects: [
      { label: "+25 Faith Zeal", isPositive: true },
      { label: "-20 Foreign Diplo", isPositive: false },
    ],
  },
];
