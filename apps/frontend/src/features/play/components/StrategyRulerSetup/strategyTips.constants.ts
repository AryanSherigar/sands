export interface StrategyTip {
  id: string;
  category: string;
  text: string;
  subtext?: string;
}

export const STRATEGY_LOADER_STAGES = [
  "Inscribing the Royal Covenant...",
  "Dispatching Heralds to the Provinces...",
  "Unfurling the Frontier Wilds...",
] as const;

export const STRATEGY_TIPS: readonly StrategyTip[] = [
  {
    id: "hover-formulas",
    category: "Simulation Clarity",
    text: "Every number can be hovered to reveal its underlying simulation formula.",
    subtext: "Transparent mechanics govern all taxation, supply, and casualty tallies.",
  },
  {
    id: "treaty-covenants",
    category: "Diplomatic Honour",
    text: "Treaties are binding covenants — breaking an oath leaves a bitter memory across rival courts.",
    subtext: "Betrayals linger in faction memories for generations.",
  },
  {
    id: "supply-lines-attrition",
    category: "Martial Logistics",
    text: "Armies marching far from friendly territory suffer attrition when supply lines stretch thin.",
    subtext: "Forage decays swiftly in harsh winter frosts and hostile territory.",
  },
  {
    id: "scouting-intel-fading",
    category: "War & Intel",
    text: "Scouting thins the fog of war and reveals enemy battle tactics, but gathered intel grows stale.",
    subtext: "Old reports may fail to show newly mobilized garrisons.",
  },
  {
    id: "crisis-escalation",
    category: "Provincial Order",
    text: "Simmering regional crises escalate each turn if left unaddressed by royal mandate.",
    subtext: "Murmurs ignite into open unrest if grievances go unanswered.",
  },
  {
    id: "reserve-timing",
    category: "Tactical Command",
    text: "Reserve forces in battle can turn the tide if deployed at the decisive round.",
    subtext: "Commit cavalry or guard units when enemy formations begin to waver.",
  },
];
