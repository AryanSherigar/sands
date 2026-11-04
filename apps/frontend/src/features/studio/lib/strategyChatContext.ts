import type { MapRegion } from "@/shared/types/strategy-map.types";
import type { AssistantStrategyContextPayload } from "../types/assistant.types";
import type { StrategyFields } from "../types/strategyDocument.types";

export interface StrategyChatContextInput {
  title: string;
  fields: StrategyFields;
  mapRegions: MapRegion[];
  activePanel: string | null;
}

export const buildStrategyChatContext = ({
  title,
  fields,
  mapRegions,
  activePanel,
}: StrategyChatContextInput): AssistantStrategyContextPayload => {
  const regionNames = new Map(mapRegions.map((region) => [region.id, region.name]));
  const regionIds = new Set([...mapRegions.map((region) => region.id), ...fields.regions.map((item) => item.region_id)]);
  const setupById = new Map(fields.regions.map((item) => [item.region_id, item]));
  return {
    title,
    timing: fields.timing,
    factions: fields.factions.map((faction) => {
      const leader = fields.leaders.find((item) => item.id === faction.leader_id);
      return {
        faction_id: faction.id,
        name: faction.name,
        leader_id: faction.leader_id,
        leader_name: leader?.name ?? "",
        leader_history: leader?.history ?? "",
        capital_region_id: faction.capital_region_id,
        treasury: faction.treasury,
        manpower: faction.manpower,
        stability: faction.stability,
        is_playable: faction.is_playable,
      };
    }),
    regions: [...regionIds].map((regionId) => {
      const setup = setupById.get(regionId);
      return {
        region_id: regionId,
        name: regionNames.get(regionId) ?? "",
        owner_id: setup?.owner_id ?? null,
        population: setup?.population ?? 0,
        wealth: setup?.wealth ?? 0,
        manpower: setup?.manpower ?? 0,
        unrest: setup?.unrest ?? 0,
        garrison: setup?.garrison ?? 0,
      };
    }),
    relations: fields.relations.map(({ faction_a, faction_b, status }) => ({ faction_a, faction_b, status })),
    claims: fields.claims,
    grudges: fields.grudges,
    armies: fields.armies.map((army) => ({
      army_id: army.id,
      owner_id: army.owner_id,
      location_id: army.location_id,
      troops: Object.fromEntries(Object.entries(army.troops).filter(([, count]) => count !== undefined)) as Record<
        string,
        number
      >,
      commander_name: fields.commanders.find((item) => item.id === army.commander_id)?.name ?? "",
    })),
    rules: { ...fields.rules },
    active_panel: activePanel ?? "",
  };
};
