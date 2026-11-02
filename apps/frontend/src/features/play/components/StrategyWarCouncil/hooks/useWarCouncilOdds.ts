import type { BattleView, StandingPlan, TacticalFactor, TacticalOddsEstimate } from "../StrategyWarCouncil.types";

export function calculateTacticalOdds(
  battle: BattleView,
  _plan: StandingPlan,
  commanderTrait?: string,
): TacticalOddsEstimate {
  const ownTroops = battle.own_contingent?.troops ?? {};
  const playerTotal = Object.values(ownTroops).reduce((acc, count) => acc + count, 0);

  const opponent = battle.opponents[0];
  const enemyMin = opponent?.strength.minimum ?? 1000;
  const enemyMax = opponent?.strength.maximum ?? 1500;
  const enemyMid = opponent?.strength.exact ?? Math.round((enemyMin + enemyMax) / 2);

  const baselineShare = Math.round((playerTotal / (playerTotal + enemyMid)) * 100);

  const factors: TacticalFactor[] = [];

  // Terrain factor
  const isHighGround = battle.terrain === "hills" || battle.terrain === "mountain";
  let terrainVal = 0;
  if (isHighGround) {
    terrainVal = 10;
  } else if (battle.terrain === "marsh") {
    terrainVal = -10;
  }
  factors.push({
    id: "terrain",
    name: `Terrain: ${battle.terrain === "hills" ? "Sloped Crest" : battle.terrain}`,
    icon: "landscape",
    valuePercent: terrainVal,
    isPositive: terrainVal >= 0,
    title: "Terrain Slope & Ground Mechanics",
    explanation: isHighGround
      ? "Holding defensive elevation against enemy charge: +15% Cohesion stabilization − 5% slope friction = +10% Net."
      : "Standard level frontage with standard engagement friction.",
  });

  // Commander trait factor
  const traitBonus = commanderTrait?.toLowerCase().includes("cautious") ? 5 : 0;
  factors.push({
    id: "commander",
    name: `Commander Trait: ${commanderTrait ? commanderTrait.charAt(0).toUpperCase() + commanderTrait.slice(1) : "Disciplined"}`,
    icon: "military_tech",
    valuePercent: traitBonus,
    isPositive: traitBonus >= 0,
    title: "Commander Stance Influence",
    explanation: traitBonus > 0
      ? "Disciplined leadership mitigates panic by +8% with a −3% hesitation delay = +5% Net Def."
      : "Standard officer command posture.",
  });

  // Logistics / Rations
  const supplyVal = battle.own_contingent?.supply === "supplied" ? 8 : -15;
  factors.push({
    id: "supply",
    name: battle.own_contingent?.supply === "supplied" ? "Full Grain Supply Rations" : "Strained Field Logistics",
    icon: "grain",
    valuePercent: supplyVal,
    isPositive: supplyVal >= 0,
    title: "Supply Logistics Formula",
    explanation: supplyVal >= 0
      ? "Cohorts on double bread rations preserve stamina beyond Round 2: +8% Net Stamina."
      : "Depleted rations reduce front-line morale and cohesion.",
  });

  // Weather dampness
  const weatherVal = battle.weather === "rain" ? -15 : 0;
  factors.push({
    id: "weather",
    name: battle.weather === "rain" ? "Weather: River Dampness & Rain" : "Weather: Clear Skies",
    icon: "cloud",
    valuePercent: weatherVal,
    isPositive: weatherVal >= 0,
    title: "Atmospheric Ballistics Penalty",
    explanation: weatherVal < 0
      ? "Bodkin bowstrings moisture absorption: Arrow velocity −18%, penetration −12%. Net range impact: −15%."
      : "Optimal ballistics trajectory and dry footing.",
  });

  // Cavalry mix deficit
  const cavalryCount = ownTroops["cavalry"] ?? 0;
  const cavVal = cavalryCount < 400 ? -12 : 5;
  factors.push({
    id: "troopmix",
    name: cavVal < 0 ? "Troop Mix: Low Heavy Horse" : "Balanced Cavalry Screen",
    icon: cavVal < 0 ? "warning" : "shield",
    valuePercent: cavVal,
    isPositive: cavVal >= 0,
    title: "Flank Protection Ledger",
    explanation: cavVal < 0
      ? "Opposing cavalry exceeds frontline mount count. Flank vulnerable to envelopment if center locks: −12% Penalty."
      : "Adequate outriders cover infantry flanks from encirclement.",
  });

  const netModifier = factors.reduce((sum, f) => sum + f.valuePercent, 0);
  const balancePercent = Math.max(10, Math.min(90, baselineShare + netModifier));

  const minShare = Math.round((playerTotal / (playerTotal + enemyMax)) * 100) + netModifier;
  const maxShare = Math.round((playerTotal / (playerTotal + enemyMin)) * 100) + netModifier;

  const isRange = !opponent?.strength.exact;
  let tierText = "Hazardous";
  if (balancePercent >= 65) {
    tierText = "Decisive";
  } else if (balancePercent >= 55) {
    tierText = "Favorable";
  } else if (balancePercent >= 45) {
    tierText = "Contested";
  }

  return {
    balancePercent,
    isRange,
    minPercent: Math.max(10, minShare),
    maxPercent: Math.min(90, maxShare),
    tierText,
    factors,
    playerLossEstimated: Math.round(playerTotal * 0.05),
    enemyLossEstimated: Math.round(enemyMid * 0.18),
    warScoreEstimated: Math.round(balancePercent * 0.5),
  };
}
