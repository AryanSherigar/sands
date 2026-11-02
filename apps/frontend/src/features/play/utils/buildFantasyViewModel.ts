import type { MasterEntity, PlaythroughData } from "../types/play.types";

export interface FantasyAttribute {
  label: string;
  value: string | number | boolean;
}

export interface FantasyCharacter {
  id: string;
  name: string;
  role: string;
  title: string;
  bio: string | null;
  disposition: { percent: number; label: string } | null;
  tacticalRole?: string;
  currentMood?: string;
  inventoryArtifact?: string;
  questLink?: string;
  frontierIntel?: string;
  avatarUrl?: string;
  initial: string;
  attributes: FantasyAttribute[];
}

export interface FantasyStatus {
  locale: string | null;
  energy: { current: number; max: number } | null;
  vault: { coins: number; label: string } | null;
}

export interface FantasyAccord {
  title: string;
  stageLabel: string;
  stageProgress: number | null;
  summary: string;
}

export interface FantasySceneImage {
  turnId: string;
  url: string;
  plateLabel?: string;
  yearLabel?: string;
}

export interface FantasyViewModel {
  location: string | null;
  characters: FantasyCharacter[];
  factions: FantasyCharacter[];
  sceneImage: FantasySceneImage | null;
  scenarioTitle: string;
  folioTitle: string;
  turnNumber: number;
  status: FantasyStatus;
  currentAccord: FantasyAccord | null;
  relics: MasterEntity[];
  tacticalInclinations: string[];
}

function resolveEntityAttrs(
  entity: MasterEntity,
  state: Record<string, unknown>,
): FantasyAttribute[] {
  const entityStates = state?.entities;
  if (!entityStates || typeof entityStates !== "object") return [];
  const live = (entityStates as Record<string, unknown>)[entity.entity_id];
  if (!live || typeof live !== "object" || Array.isArray(live)) return [];
  return Object.entries(entity.attributes_schema ?? {}).flatMap(([key, def]) => {
    const val = (live as Record<string, unknown>)[key];
    if (typeof val !== "string" && typeof val !== "number" && typeof val !== "boolean") return [];
    return [{ label: def.label ?? key, value: val }];
  });
}

function resolveCharacter(
  entity: MasterEntity,
  state: Record<string, unknown>,
): FantasyCharacter {
  const attrs = resolveEntityAttrs(entity, state);
  const rawRole = attrs.find((a) => a.label.toLowerCase().includes("role"))?.value;

  return {
    id: entity.entity_id,
    name: entity.canonical_name,
    role: typeof rawRole === "string" ? rawRole : "Personnel",
    title: entity.description ?? "",
    bio: entity.description,
    disposition: null,
    tacticalRole: attrs.find((a) => a.label.toLowerCase().includes("tactical"))?.value?.toString(),
    currentMood: attrs.find((a) => a.label.toLowerCase().includes("mood"))?.value?.toString(),
    inventoryArtifact: attrs.find((a) => a.label.toLowerCase().includes("inventory"))?.value?.toString(),
    questLink: attrs.find((a) => a.label.toLowerCase().includes("quest"))?.value?.toString(),
    frontierIntel: attrs.find((a) => a.label.toLowerCase().includes("intel"))?.value?.toString(),
    initial: entity.canonical_name.slice(0, 1).toUpperCase(),
    attributes: attrs,
  };
}

function resolveStatus(playthrough: PlaythroughData, locName: string | null): FantasyStatus {
  const pState = playthrough.state?.player as Record<string, unknown> | undefined;
  const pStats = playthrough.player_stats;

  const coinsFromState = typeof pState?.coins === "number" ? pState.coins : undefined;
  const coinsFromStats = pStats?.find((s) => s.key === "coins" || s.key === "gold")?.value;
  let rawCoins: number | null = null;
  if (typeof coinsFromState === "number") {
    rawCoins = coinsFromState;
  } else if (typeof coinsFromStats === "number") {
    rawCoins = coinsFromStats;
  }

  const energyFromState = typeof pState?.energy === "number" ? pState.energy : undefined;
  const energyFromStats = pStats?.find((s) => s.key === "energy" || s.key === "spark")?.value;
  let rawEnergy: number | null = null;
  if (typeof energyFromState === "number") {
    rawEnergy = energyFromState;
  } else if (typeof energyFromStats === "number") {
    rawEnergy = energyFromStats;
  }

  const rawMax = playthrough.fantasy_mechanics?.energy_max;
  const energyMax = typeof rawMax === "number" && rawMax > 0 ? rawMax : null;

  return {
    locale: locName,
    energy: rawEnergy !== null && energyMax !== null ? { current: rawEnergy, max: energyMax } : null,
    vault: rawCoins !== null ? { coins: rawCoins, label: String(rawCoins) } : null,
  };
}

function resolveAccord(playthrough: PlaythroughData): FantasyAccord | null {
  const quests = playthrough.state?.quests as Record<string, unknown> | undefined;
  const retrieval = quests?.retrieval as Record<string, unknown> | undefined;
  const stage = typeof retrieval?.stage === "string" ? retrieval.stage : null;
  const stageMap: Record<string, string> = {
    offered: "Offered",
    accepted: "Accepted",
    body_recovered: "Body recovered",
    cremated: "Cremated",
    rewarded: "Rewarded",
  };

  if (playthrough.fantasy_mechanics?.profile === "zegaris" && stage && stageMap[stage]) {
    return {
      title: "Retrieval mission",
      stageLabel: stageMap[stage],
      stageProgress: null,
      summary: "",
    };
  }
  if (Array.isArray(playthrough.objectives) && playthrough.objectives.length > 0) {
    const obj = playthrough.objectives[0];
    return {
      title: obj.outcome_title,
      stageLabel: "Active Accord",
      stageProgress: null,
      summary: obj.outcome_text,
    };
  }
  return null;
}

function resolveSceneImage(playthrough: PlaythroughData): FantasySceneImage | null {
  const turns = playthrough.turns ?? [];
  const imgTurn = [...turns].reverse().find((t) => Boolean(t.image_url));
  if (!imgTurn?.image_url) return null;
  return {
    turnId: imgTurn.id,
    url: imgTurn.image_url,
  };
}

export function buildFantasyViewModel(playthrough: PlaythroughData): FantasyViewModel {
  const entities = playthrough.entities ?? [];
  const turns = playthrough.turns ?? [];
  const state = playthrough.state ?? {};
  const locEntity = entities.find(
    (e) => e.entity_type === "location" && e.entity_id === state.current_location_id,
  );
  const locName = locEntity?.canonical_name ?? null;
  const chars = entities.filter((e) => e.entity_type === "character").map((e) => resolveCharacter(e, state));
  const facs = entities.filter((e) => e.entity_type === "faction" || e.entity_type === "organization").map((e) => resolveCharacter(e, state));
  const sceneImg = resolveSceneImage(playthrough);
  const accord = resolveAccord(playthrough);
  const status = resolveStatus(playthrough, locName);

  const chips = Array.isArray(playthrough.action_chips) ? playthrough.action_chips : [];

  return {
    location: locName,
    characters: chars,
    factions: facs,
    sceneImage: sceneImg,
    scenarioTitle: playthrough.scenario_title || "Chronicle",
    folioTitle: locName ? `FOLIO · ${locName.toUpperCase()}` : "CHRONICLE FOLIO",
    turnNumber: turns.length + 1,
    status,
    currentAccord: accord,
    relics: playthrough.player_inventory ?? [],
    tacticalInclinations: chips,
  };
}
