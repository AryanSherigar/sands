import type {
  AmbientTerrain,
  StrategicMood,
  StrategyAudioTarget,
  StrategyContextTrack,
  StrategyStingerEvent,
  StrategyUIContext,
} from "@/shared/types/strategy-audio.types";
import type {
  StrategyWorldSnapshot,
  StrategyWorldSnapshotEvent,
} from "@/features/play/types/strategyPlay.types";

function resolveTerrain(terrain?: string): AmbientTerrain {
  if (!terrain) return "plains";
  const normalized = terrain.toLowerCase();
  if (normalized.includes("arid") || normalized.includes("desert") || normalized.includes("dune")) {
    return "arid";
  }
  if (normalized.includes("mount") || normalized.includes("cairn") || normalized.includes("hill")) {
    return "mountains";
  }
  if (normalized.includes("coast") || normalized.includes("sea") || normalized.includes("port")) {
    return "coast";
  }
  return "plains";
}

function resolveStinger(
  events: StrategyWorldSnapshotEvent[] | undefined,
  currentTurn: number,
  lastPlayedTurn?: number,
): StrategyStingerEvent | null {
  if (!events || events.length === 0) return null;
  if (lastPlayedTurn !== undefined && lastPlayedTurn >= currentTurn) return null;

  const currentTurnEvents = events.filter((e) => e.turn === currentTurn);
  for (const event of currentTurnEvents) {
    const rawType = (event.event_type ?? event.type ?? "");
    const type = typeof rawType === "string" ? rawType.toUpperCase() : "";
    if (type.includes("WAR_DECLARED") || type.includes("WAR_START")) return "war_declared";
    if (type.includes("TREATY") || type.includes("PACT") || type.includes("PEACE")) return "treaty_signed";
    if (type.includes("UPRISING") || type.includes("REVOLT") || type.includes("REBEL")) return "uprising";
    if (type.includes("SUCCESSION") || type.includes("RULER_DIED")) return "succession";
  }
  return null;
}

export function evaluateStrategyAudio(
  worldState: StrategyWorldSnapshot,
  uiContext: StrategyUIContext,
  _seed: string,
  lastPlayedTurn?: number,
): StrategyAudioTarget {
  const myFactionId = worldState.my_faction?.id;
  const isWinter = (worldState.season ?? "").toLowerCase() === "winter";

  // 1. Terrain derivation
  const capitalId = worldState.my_faction?.capital_region_id;
  const capitalRegion = worldState.regions?.find((r) => r.id === capitalId) ?? worldState.regions?.[0];
  const ambientTrack = resolveTerrain(capitalRegion?.terrain);

  // 2. War intensity W
  let warIntensity = 0.0;
  const activeWars = (worldState.wars ?? []).filter(
    (w) => w.attacker_faction_id === myFactionId || w.defender_faction_id === myFactionId,
  );
  if (activeWars.length > 0) {
    warIntensity = 0.6;
    const hasSiege = worldState.regions?.some(
      (r) => r.owner_faction_id === myFactionId && (Boolean(r.is_under_siege) || (r.siege_progress ?? 0) > 0),
    );
    if (hasSiege) warIntensity = Math.min(1.0, warIntensity + 0.3);
  }

  // 3. Realm Strain S
  const ownedRegions = (worldState.regions ?? []).filter((r) => r.owner_faction_id === myFactionId);
  const avgUnrest =
    ownedRegions.length > 0
      ? ownedRegions.reduce((sum, r) => sum + (r.unrest ?? 0), 0) / ownedRegions.length
      : 0;
  const isBankrupt = (worldState.my_faction?.treasury ?? 0) < 0;
  const realmStrain = (avgUnrest / 100) * 0.6 + (isBankrupt ? 0.4 : 0.0);

  // 4. Strategic Mood Tier Selection
  let strategicMood: StrategicMood = "pax";
  let baseMoodGain = 0.6;

  if (warIntensity >= 0.5) {
    strategicMood = "war";
    baseMoodGain = 0.7;
  } else if (realmStrain >= 0.55 || avgUnrest >= 70) {
    strategicMood = "desolation";
    baseMoodGain = 0.6;
  } else if (realmStrain >= 0.25 || activeWars.length > 0) {
    strategicMood = "vigilance";
    baseMoodGain = 0.5;
  } else {
    strategicMood = "pax";
    baseMoodGain = 0.6;
  }

  // 5. Context Ducking & Layer 3 Gains
  let contextTrack: StrategyContextTrack = "none";
  let contextGain = 0.0;
  let moodDuckingFactor = 1.0;

  switch (uiContext) {
    case "negotiation":
      contextTrack = "court";
      contextGain = 0.4;
      moodDuckingFactor = 0.5;
      break;
    case "letter":
      contextTrack = "study";
      contextGain = 0.45;
      moodDuckingFactor = 0.4;
      break;
    case "war_council":
      contextTrack = "tactical";
      contextGain = 0.5;
      moodDuckingFactor = 0.6;
      break;
    case "turn_report":
      contextTrack = "none";
      contextGain = 0.0;
      moodDuckingFactor = 0.7;
      break;
    case "event":
      contextTrack = "court";
      contextGain = 0.3;
      moodDuckingFactor = 0.5;
      break;
    case "map":
    default:
      contextTrack = "none";
      contextGain = 0.0;
      moodDuckingFactor = 1.0;
      break;
  }

  // 6. Stinger derivation
  const pendingStinger = resolveStinger(worldState.event_log, worldState.turn ?? 1, lastPlayedTurn);

  return {
    ambientTrack,
    ambientGain: 0.2,
    isWinterMuffled: isWinter,
    strategicMood,
    moodGain: baseMoodGain * moodDuckingFactor,
    contextTrack,
    contextGain,
    pendingStinger,
  };
}
