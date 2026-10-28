import type { CampaignWorldView, RegionView } from "../../types/simulation.types";

const PREVIEW_FACTION_ID = "f-valenreach";

const buildPreviewRegion = (
  regionId: string,
  ownerId: string | null,
  terrain: string,
  unrest: number,
): RegionView => ({
  region_id: regionId,
  owner_id: ownerId,
  terrain,
  visibility: "visible",
  detail: {
    id: regionId,
    owner_id: ownerId,
    population: 42800,
    wealth: 42,
    manpower: 1850,
    unrest,
    garrison: 1200,
    faith_id: "high-orthodoxy",
    improvements: [{ kind: "fort", turns_remaining: 0 }],
    claimant_ids: [],
    conversion_turns_remaining: 0,
  },
});

export const DEFAULT_PREVIEW_WORLD: CampaignWorldView = {
  world_version: 1,
  turn: 1,
  wave: 0,
  status: "planning",
  battles: [],
  clock: { turn: 1, start_year: 1042, start_month: 7 },
  my_faction: {
    id: PREVIEW_FACTION_ID,
    treasury: 340,
    manpower: 14200,
    stability: 2,
    war_exhaustion: 0,
    reputation: 50,
    tax_rate: "normal",
    loans: [],
  },
  ruler: { name: "King Alden IV" },
  regions: [
    buildPreviewRegion("reg-dunmere", PREVIEW_FACTION_ID, "plain", 14),
    buildPreviewRegion("reg-greenford", PREVIEW_FACTION_ID, "forest", 52),
    { region_id: "reg-highcrag", owner_id: "f-ironmark", terrain: "mountain", visibility: "fogged" },
    { region_id: "reg-silverwood", owner_id: null, terrain: "coast", visibility: "visible" },
  ],
  armies: [
    {
      army_id: "army-royal-1",
      owner_id: PREVIEW_FACTION_ID,
      location_id: "reg-dunmere",
      commander_name: "1st Royal Host",
      troops: { infantry: 3600, cavalry: 1200 },
    },
    {
      army_id: "army-ironmark-1",
      owner_id: "f-ironmark",
      location_id: "reg-highcrag",
      commander_name: "Ironmark Host",
      troops: { cavalry: 2000 },
    },
  ],
  rivals: [
    {
      faction_id: "f-oakhaven",
      name: "Duchy of Oakhaven",
      leader_name: "Duke Cedric",
      relation: "alliance",
      treasury_range: { low: 300, high: 600 },
      manpower_range: { low: 8000, high: 12000 },
    },
    {
      faction_id: "f-ironmark",
      name: "Ironmark March",
      leader_name: "Warlord Brand",
      relation: "war",
      treasury_range: { low: 150, high: 400 },
      manpower_range: { low: 14000, high: 20000 },
    },
  ],
  queued_orders: [
    {
      id: "cmd-1",
      order: {
        kind: "move_army",
        faction_id: PREVIEW_FACTION_ID,
        army_id: "army-royal-1",
        to_region_id: "reg-greenford",
      },
      cost: 1,
      queued_turn: 1,
      is_cancellable: true,
    },
    {
      id: "cmd-2",
      order: {
        kind: "set_tax_rate",
        faction_id: PREVIEW_FACTION_ID,
        tax_rate: "low",
      },
      cost: 1,
      queued_turn: 1,
      is_cancellable: true,
    },
  ],
  orders_remaining: 4,
};
