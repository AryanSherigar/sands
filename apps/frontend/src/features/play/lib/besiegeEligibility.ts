import type { ArmyView, CampaignWorldView } from "../types/simulation.types";

const WAR_RELATIONS = new Set(["war", "at_war"]);

export function canBesiegeFrom(army: ArmyView, world: CampaignWorldView): boolean {
  if (army.owner_id !== world.my_faction.id) return false;
  const region = world.regions.find((item) => item.region_id === army.location_id);
  if (!region?.owner_id || region.owner_id === world.my_faction.id) return false;
  if (region.occupation || region.siege) return false;
  const rival = world.rivals.find((item) => item.faction_id === region.owner_id);
  return rival !== undefined && WAR_RELATIONS.has(rival.relation);
}
