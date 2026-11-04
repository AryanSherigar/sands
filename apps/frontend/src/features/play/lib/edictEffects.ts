const EFFECT_LABELS: Record<string, (amount: number) => string> = {
  manpower_regen_percent: (amount) => `${signed(amount)}% manpower regrowth`,
  unrest_per_turn: (amount) => `${signed(amount)} unrest each turn`,
  tax_percent_points: (amount) => `${signed(amount)} points of tax`,
  trade_efficiency_percent: (amount) => `${signed(amount)}% trade income`,
};

function signed(amount: number): string {
  return amount > 0 ? `+${amount}` : `${amount}`;
}

export function describeEdictEffects(modifiers: Record<string, number> | undefined): string[] {
  if (!modifiers) return [];
  return Object.entries(modifiers)
    .filter(([key, amount]) => key in EFFECT_LABELS && amount !== 0)
    .map(([key, amount]) => EFFECT_LABELS[key]!(amount));
}
