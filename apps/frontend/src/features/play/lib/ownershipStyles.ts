import {
  FOG_MODE_SHADOW_FILL_CLASS,
  FOG_MODE_VISIBLE_FILL_CLASS,
  FOGGED_FILL_CLASS,
  FOGGED_STROKE_CLASS,
  LANTERN_STROKE_CLASS,
  NEUTRAL_FILL_CLASS,
  OCCUPIED_STROKE_CLASS,
  OWN_FACTION_FILL_CLASS,
  RIVAL_FILL_CLASSES,
} from "../constants/ownershipPalette";
import type { StrategyMapMode } from "../stores/strategyPlay.types";
import type { RegionView } from "../types/simulation.types";

function listRivalIds(regions: RegionView[], myFactionId: string): string[] {
  const ownerIds = regions
    .map((region) => region.owner_id)
    .filter((ownerId): ownerId is string => ownerId !== null && ownerId !== myFactionId);
  return [...new Set(ownerIds)].sort();
}

function getFogModeFillClass(visibility: string): string {
  return visibility === "visible"
    ? FOG_MODE_VISIBLE_FILL_CLASS
    : FOG_MODE_SHADOW_FILL_CLASS;
}

function getPoliticalFillClass(
  region: RegionView,
  myFactionId: string,
  rivalIds: string[],
): string {
  if (region.visibility === "fogged" && region.owner_id !== myFactionId) {
    return FOGGED_FILL_CLASS;
  }
  if (region.owner_id === myFactionId) {
    return OWN_FACTION_FILL_CLASS;
  }
  if (region.owner_id === null) {
    return NEUTRAL_FILL_CLASS;
  }
  const rivalIndex = rivalIds.indexOf(region.owner_id);
  return RIVAL_FILL_CLASSES[rivalIndex % RIVAL_FILL_CLASSES.length];
}

export function buildOwnershipFillClasses(
  regions: RegionView[],
  myFactionId: string,
  activeMapMode?: StrategyMapMode,
): Record<string, string> {
  const rivalIds = listRivalIds(regions, myFactionId);
  const fills: Record<string, string> = {};
  for (const region of regions) {
    fills[region.region_id] =
      activeMapMode === "fog"
        ? getFogModeFillClass(region.visibility)
        : getPoliticalFillClass(region, myFactionId, rivalIds);
  }
  return fills;
}

function getRegionStrokeClass(
  region: RegionView,
  myFactionId: string,
  activeMapMode?: StrategyMapMode,
): string {
  if (activeMapMode === "fog") {
    return region.visibility === "visible"
      ? LANTERN_STROKE_CLASS
      : FOGGED_STROKE_CLASS;
  }
  if (region.occupation || region.siege) return OCCUPIED_STROKE_CLASS;
  const isVisible =
    region.visibility === "visible" || region.owner_id === myFactionId;
  return isVisible ? LANTERN_STROKE_CLASS : FOGGED_STROKE_CLASS;
}

export function buildRegionStrokeClasses(
  regions: RegionView[],
  myFactionId: string,
  activeMapMode?: StrategyMapMode,
): Record<string, string> {
  const strokes: Record<string, string> = {};
  for (const region of regions) {
    strokes[region.region_id] = getRegionStrokeClass(
      region,
      myFactionId,
      activeMapMode,
    );
  }
  return strokes;
}
