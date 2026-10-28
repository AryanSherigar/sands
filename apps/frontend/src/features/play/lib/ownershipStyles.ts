import {
  NEUTRAL_FILL_CLASS,
  OWN_FACTION_FILL_CLASS,
  RIVAL_FILL_CLASSES,
} from "../constants/ownershipPalette";
import type { RegionView } from "../types/simulation.types";

function listRivalIds(regions: RegionView[], myFactionId: string): string[] {
  const ownerIds = regions
    .map((region) => region.owner_id)
    .filter((ownerId): ownerId is string => ownerId !== null && ownerId !== myFactionId);
  return [...new Set(ownerIds)].sort();
}

export function buildOwnershipFillClasses(
  regions: RegionView[],
  myFactionId: string,
): Record<string, string> {
  const rivalIds = listRivalIds(regions, myFactionId);
  const fills: Record<string, string> = {};
  for (const region of regions) {
    if (region.owner_id === null) {
      fills[region.region_id] = NEUTRAL_FILL_CLASS;
    } else if (region.owner_id === myFactionId) {
      fills[region.region_id] = OWN_FACTION_FILL_CLASS;
    } else {
      const rivalIndex = rivalIds.indexOf(region.owner_id);
      fills[region.region_id] = RIVAL_FILL_CLASSES[rivalIndex % RIVAL_FILL_CLASSES.length];
    }
  }
  return fills;
}
