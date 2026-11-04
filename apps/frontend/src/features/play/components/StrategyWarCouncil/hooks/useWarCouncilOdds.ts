import type {
  BattleOutlook,
  BattleView,
  OutlookFactor,
  TacticalFactor,
  TacticalOddsEstimate,
} from "../StrategyWarCouncil.types";

const NEUTRAL_FACTOR_PERCENT = 100;
const DECISIVE_SHARE_PERCENT = 65;
const FAVORABLE_SHARE_PERCENT = 55;
const CONTESTED_SHARE_PERCENT = 45;

const FACTOR_COPY: Record<string, { name: string; icon: string; explanation: string }> = {
  formation: {
    name: "Formation",
    icon: "shield",
    explanation: "How your standing formation scales your attack pressure each exchange.",
  },
  tactic: {
    name: "Tactic",
    icon: "military_tech",
    explanation: "How your chosen tactic scales your attack pressure each exchange.",
  },
  weather: {
    name: "Weather",
    icon: "cloud",
    explanation: "How today's weather scales attack pressure for your troops.",
  },
  supply: {
    name: "Supply",
    icon: "grain",
    explanation: "How your supply state scales attack pressure for your troops.",
  },
};

function describeShare(sharePercent: number): string {
  if (sharePercent >= DECISIVE_SHARE_PERCENT) return "Decisive";
  if (sharePercent >= FAVORABLE_SHARE_PERCENT) return "Favorable";
  if (sharePercent >= CONTESTED_SHARE_PERCENT) return "Contested";
  return "Hazardous";
}

function toTacticalFactor(factor: OutlookFactor): TacticalFactor {
  const copy = FACTOR_COPY[factor.id] ?? { name: factor.id, icon: "tune", explanation: "" };
  const delta = factor.percent - NEUTRAL_FACTOR_PERCENT;
  return {
    id: factor.id,
    name: copy.name,
    icon: copy.icon,
    valuePercent: delta,
    isPositive: delta >= 0,
    title: `${copy.name} modifier`,
    explanation: copy.explanation,
  };
}

function fromOutlook(outlook: BattleOutlook): TacticalOddsEstimate {
  return {
    balancePercent: outlook.own_share_percent,
    tierText: describeShare(outlook.own_share_percent),
    confidence: outlook.confidence,
    basis: outlook.basis,
    factors: outlook.factors.map(toTacticalFactor),
    playerLoss: outlook.own_losses,
    enemyLoss: outlook.enemy_losses,
  };
}

export function calculateTacticalOdds(battle: BattleView): TacticalOddsEstimate | null {
  return battle.outlook ? fromOutlook(battle.outlook) : null;
}
