import { useState, useMemo, useCallback } from "react";
import { apiClient } from "@/shared/lib/api-client";
import type {
  StrategyAmbition,
  StrategyRulerState,
  StrategyTrait,
  PlayableFactionInfo,
} from "./StrategyRulerSetup.types";
import { BUILTIN_STRATEGY_TRAITS } from "./builtinTraits";
import { BUILTIN_STRATEGY_AMBITIONS } from "./builtinAmbitions";

export interface StrategySetupValidationErrors {
  name?: string;
  traits?: string;
  ambitions?: string;
  faction?: string;
}

export interface UseStrategySetupStateReturn {
  activeFactionId: string;
  setActiveFactionId: (factionId: string) => void;
  ruler: StrategyRulerState;
  updateRuler: (updates: Partial<StrategyRulerState>) => void;
  isRedrafting: boolean;
  redraftBackstory: () => Promise<void>;
  restoreDefaultRuler: () => void;
  validation: StrategySetupValidationErrors;
  isValid: boolean;
  factions: PlayableFactionInfo[];
  availableTraits: StrategyTrait[];
  availableAmbitions: StrategyAmbition[];
  activeFaction: PlayableFactionInfo | undefined;
}

interface ScenarioLike {
  scenario_id?: string;
  id?: string;
  strategy_document?: {
    factions?: Array<{
      id?: string;
      name?: string;
      color?: string;
      is_playable?: boolean;
      provinces_count?: number;
      capital_seat?: string;
      capital_name?: string;
      government?: string;
      treasury?: number;
      manpower?: number;
      stability?: number;
      capital_region_id?: string | null;
      leader_id?: string | null;
      role_tag?: string;
      tagline?: string;
      crisis?: {
        title: string;
        tag?: string;
        description: string;
      };
    }>;
    leaders?: Array<{
      id?: string;
      faction_id?: string;
      name?: string;
      epithet?: string;
      portrait_url?: string;
      portraitUrl?: string;
      trait_ids?: string[];
      ambition_ids?: string[];
      history?: string;
      backstory?: string;
      dynasty_name?: string;
      house_motto?: string;
      houseMotto?: string;
      house_badge?: string;
      houseBadge?: string;
    }>;
    traits?: StrategyTrait[];
    ambitions?: StrategyAmbition[];
  };
}

const DEFAULT_FACTIONS: PlayableFactionInfo[] = [
  {
    id: "valenreach",
    name: "Crown of Valenreach",
    color: "#46606E",
    is_playable: true,
    provinces_count: 4,
    capital_seat: "Castle Highgard",
    government: "Feudal Monarchy",
    treasury: 340,
    manpower: 14200,
    role_tag: "Diplomatic",
    tagline: "Ancient lineage of the high court",
    crisis: {
      title: "Succession Dispute",
      tag: "Crisis",
      description:
        "Rival claimants challenge the sovereign legitimacy along the western marches.",
    },
  },
  {
    id: "oakhaven",
    name: "Duchy of Oakhaven",
    color: "#5E8A5A",
    is_playable: true,
    provinces_count: 3,
    capital_seat: "Oakhaven Spire",
    government: "Duchy",
    treasury: 250,
    manpower: 8900,
    role_tag: "Stewardship",
    tagline: "Verdant forests and deep granite quarries",
  },
];

function deriveLeaderDefaults(
  factionId: string,
  factions: PlayableFactionInfo[],
  leaders: NonNullable<ScenarioLike["strategy_document"]>["leaders"] = [],
): StrategyRulerState {
  const faction = factions.find((f) => f.id === factionId);
  const leader = leaders.find(
    (l) =>
      (faction?.leader_id && l.id === faction.leader_id) ||
      l.faction_id === factionId,
  );

  if (leader) {
    return {
      name: leader.name || "Sovereign",
      epithet: leader.epithet || "Ruler of the Realm",
      portraitUrl: leader.portrait_url || leader.portraitUrl || "",
      traitIds:
        Array.isArray(leader.trait_ids) && leader.trait_ids.length > 0
          ? [...leader.trait_ids]
          : ["cautious", "honorable"],
      ambitionIds:
        Array.isArray(leader.ambition_ids) && leader.ambition_ids.length > 0
          ? [...leader.ambition_ids]
          : ["ambition_peace"],
      backstory: leader.history || leader.backstory || "",
      dynastyName: leader.dynasty_name || faction?.name || "",
      houseMotto: leader.house_motto || leader.houseMotto || "",
      houseBadge: leader.house_badge || leader.houseBadge || "",
    };
  }

  return {
    name: faction?.name ? `Ruler of ${faction.name}` : "Sovereign",
    epithet: "The Resolute",
    portraitUrl: "",
    traitIds: ["cautious", "honorable"],
    ambitionIds: ["ambition_peace"],
    backstory: "",
    dynastyName: faction?.name || "",
    houseMotto: "",
    houseBadge: "",
  };
}

export function useStrategySetupState(
  scenario?: ScenarioLike | null,
): UseStrategySetupStateReturn {
  const scenarioId = scenario?.scenario_id || scenario?.id || "";
  const strategyDoc = scenario?.strategy_document;
  const rawFactions = strategyDoc?.factions;
  const leaders = useMemo(
    () => strategyDoc?.leaders ?? [],
    [strategyDoc?.leaders],
  );

  const factions: PlayableFactionInfo[] = useMemo(() => {
    if (Array.isArray(rawFactions) && rawFactions.length > 0) {
      return rawFactions.map((f, idx) => ({
        id: f.id ?? `faction_${idx}`,
        name: f.name ?? "Unnamed Realm",
        color:
          f.color ?? ["#46606E", "#5E8A5A", "#A8483E", "#D2A94A"][idx % 4],
        is_playable: f.is_playable ?? true,
        provinces_count: f.provinces_count ?? 3,
        capital_seat: f.capital_seat ?? f.capital_name ?? "High Citadel",
        government: f.government ?? "Feudal Monarchy",
        treasury: typeof f.treasury === "number" ? f.treasury : 300,
        manpower: typeof f.manpower === "number" ? f.manpower : 10000,
        stability: f.stability ?? 2,
        capital_region_id: f.capital_region_id ?? null,
        leader_id: f.leader_id ?? null,
        role_tag: f.role_tag,
        tagline: f.tagline,
        crisis: f.crisis,
      }));
    }
    return DEFAULT_FACTIONS;
  }, [rawFactions]);

  const initialFactionId = useMemo(() => {
    const playable = factions.filter((f) => f.is_playable !== false);
    return playable[0]?.id ?? factions[0]?.id ?? "valenreach";
  }, [factions]);

  const [activeFactionId, setActiveFactionIdState] =
    useState<string>(initialFactionId);

  const [ruler, setRuler] = useState<StrategyRulerState>(() =>
    deriveLeaderDefaults(initialFactionId, factions, leaders),
  );

  const [isRedrafting, setIsRedrafting] = useState<boolean>(false);

  const activeFaction = useMemo(
    () => factions.find((f) => f.id === activeFactionId) ?? factions[0],
    [factions, activeFactionId],
  );

  const setActiveFactionId = useCallback(
    (factionId: string) => {
      setActiveFactionIdState(factionId);
      setRuler(deriveLeaderDefaults(factionId, factions, leaders));
    },
    [factions, leaders],
  );

  const restoreDefaultRuler = useCallback(() => {
    setRuler(deriveLeaderDefaults(activeFactionId, factions, leaders));
  }, [activeFactionId, factions, leaders]);

  const updateRuler = useCallback((updates: Partial<StrategyRulerState>) => {
    setRuler((prev) => ({ ...prev, ...updates }));
  }, []);

  const redraftBackstory = useCallback(async () => {
    if (!activeFactionId) return;
    setIsRedrafting(true);
    const payload = {
      scenario_id: scenarioId,
      faction_id: activeFactionId,
      ruler_name: ruler.name,
      epithet: ruler.epithet || null,
      trait_ids: ruler.traitIds,
      ambition_ids: ruler.ambitionIds,
    };
    try {
      const { data } = await apiClient.post<{ backstory: string }>(
        "/api/v1/strategy/ruler-backstory",
        payload,
      );
      if (data?.backstory) {
        setRuler((prev) => ({ ...prev, backstory: data.backstory }));
      }
    } catch {
      try {
        const { data } = await apiClient.post<{ backstory: string }>(
          "/v1/strategy/ruler-backstory",
          payload,
        );
        if (data?.backstory) {
          setRuler((prev) => ({ ...prev, backstory: data.backstory }));
        }
      } catch (err) {
        console.error("Failed to redraft backstory:", err);
      }
    } finally {
      setIsRedrafting(false);
    }
  }, [
    scenarioId,
    activeFactionId,
    ruler.name,
    ruler.epithet,
    ruler.traitIds,
    ruler.ambitionIds,
  ]);

  const validation = useMemo<StrategySetupValidationErrors>(() => {
    const errors: StrategySetupValidationErrors = {};
    if (!ruler.name || !ruler.name.trim()) {
      errors.name = "Ruler regnal name is required.";
    }
    if (ruler.traitIds.length < 2 || ruler.traitIds.length > 3) {
      errors.traits = "Select between 2 and 3 virtues.";
    }
    if (ruler.ambitionIds.length < 1 || ruler.ambitionIds.length > 2) {
      errors.ambitions = "Select between 1 and 2 coronation ambitions.";
    }
    if (!activeFactionId) {
      errors.faction = "A sovereign realm must be selected.";
    }
    return errors;
  }, [ruler.name, ruler.traitIds, ruler.ambitionIds, activeFactionId]);

  const isValid = Object.keys(validation).length === 0;

  const availableTraits = useMemo(() => {
    const custom = strategyDoc?.traits ?? [];
    const merged = new Map<string, StrategyTrait>();
    BUILTIN_STRATEGY_TRAITS.forEach((t) => merged.set(t.id, t));
    custom.forEach((t) => merged.set(t.id, t));
    return Array.from(merged.values());
  }, [strategyDoc?.traits]);

  const availableAmbitions = useMemo(() => {
    const custom = strategyDoc?.ambitions ?? [];
    const merged = new Map<string, StrategyAmbition>();
    BUILTIN_STRATEGY_AMBITIONS.forEach((a) => merged.set(a.id, a));
    custom.forEach((a) => merged.set(a.id, a));
    return Array.from(merged.values());
  }, [strategyDoc?.ambitions]);

  return {
    activeFactionId,
    setActiveFactionId,
    ruler,
    updateRuler,
    isRedrafting,
    redraftBackstory,
    restoreDefaultRuler,
    validation,
    isValid,
    factions,
    availableTraits,
    availableAmbitions,
    activeFaction,
  };
}
