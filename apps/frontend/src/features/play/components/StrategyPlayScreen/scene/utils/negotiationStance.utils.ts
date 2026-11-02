export function deriveLeaderMoodTag(traitIds: string[], isAtWar = false): string {
  const traits = new Set(traitIds.map((t) => t.toLowerCase()));

  if (isAtWar) {
    if (traits.has("bellicose") || traits.has("cruel") || traits.has("zealot")) {
      return "Unyielding — Hostile";
    }
    if (traits.has("cautious") || traits.has("proud") || traits.has("paranoid")) {
      return "Guarded — Distrustful";
    }
    return "Stern — Guarded";
  }

  if (traits.has("pragmatic") || traits.has("cunning")) {
    return "Calculating — Attentive";
  }
  if (traits.has("honorable") || traits.has("diplomatic")) {
    return "Cordial — Receptive";
  }
  return "Measured — Reserved";
}

export function calculateExchangeDots(exchangesRemaining: number, totalCap = 6) {
  const clampedCap = Math.max(1, totalCap);
  const remaining = Math.max(0, Math.min(exchangesRemaining, clampedCap));
  const usedCount = clampedCap - remaining;
  const activeDots = Array.from({ length: clampedCap }, (_, i) => i < usedCount);

  return { usedCount, totalCap: clampedCap, activeDots };
}

export function generateHeraldicCrestSvg(factionName: string, factionColor = "#46606E"): string {
  const initial = (factionName.trim()[0] ?? "F").toUpperCase();
  const encodedColor = encodeURIComponent(factionColor);
  return `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120" width="100%" height="100%"><path d="M50 5 L90 20 L90 70 Q50 115 50 115 Q10 70 10 20 Z" fill="${encodedColor}" stroke="%23D2A94A" stroke-width="4"/><text x="50" y="70" font-family="serif" font-size="44" font-weight="bold" fill="%23F7F0DC" text-anchor="middle">${initial}</text></svg>`;
}
