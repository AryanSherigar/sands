import { useEffect } from "react";
import { usePlayStore } from "../stores/play.store";
import { FantasyPlayScreen } from "../components/PlayScreen/Fantasy/FantasyPlayScreen";
import type { PlaythroughData } from "../types/play.types";

const PREVIEW_PLAYTHROUGH: PlaythroughData = {
  playthrough_id: "fantasy-preview-session",
  scenario_id: "scen_gilded_crown",
  scenario_title: "The Gilded Crown",
  mode: "master",
  genre_tags: ["High Fantasy"],
  fantasy_mechanics: {
    version: 1,
    profile: "zegaris",
    energy_max: 100,
    initial_energy: 85,
    rest_cost: 5,
    bounty_reward: 75,
  },
  action_chips: [
    "Inquire of the cracked wax cipher cylinder",
    "Order spiced tavern mead for Valerie",
    "Weave Minor Glamer over the runic seal",
  ],
  enabled_tools: [],
  creator_name: "Grand Archivist",
  opening_premise:
    "The stone hearth of the Hearth & Anchor roars against the mountain sleet...",
  world_lore: "Border stones broken from within. Frontier oaths hang by a thread.",
  key_facts: [
    "The Oakhaven seals were shattered from inside",
    "Valerie commands the river ford contingent",
  ],
  story_cards: [],
  character_name: "Knight Inquisitor",
  custom_fields: [],
  is_spectator: false,
  participant_id: "participant-preview-1",
  can_act: true,
  next_actor_label: null,
  active_conditions: [],
  objectives: [
    {
      outcome_title: "The Shattered Seal of Oakhaven",
      outcome_tag: "win",
      outcome_text:
        "Sylas reveals the border stones were broken from within. Valerie demands proof before committing her banner.",
    },
  ],
  player_stats: [
    { key: "coins", label: "Imperial Sovereigns", value: 142 },
    { key: "energy", label: "Arcane Spark", value: 85 },
  ],
  player_inventory: [
    {
      entity_id: "item_compass",
      entity_type: "item",
      canonical_name: "Brass Cartographer Compass",
      aliases: [],
      description: "An intricate brass compass engraved with celestial filigree.",
      attributes_schema: {},
      obtainable: true,
      attributes: {},
    },
    {
      entity_id: "item_blade",
      entity_type: "item",
      canonical_name: "Consecrated High Court Blade",
      aliases: [],
      description: "A ceremonial runic broadsword bearing the inquisitor sigil.",
      attributes_schema: {},
      obtainable: true,
      attributes: {},
    },
  ],
  entities: [
    {
      entity_id: "loc_hearth_anchor",
      entity_type: "location",
      canonical_name: "The Hearth & Anchor Tavern",
      aliases: [],
      description: "A bustling guildhall tavern at the edge of the Ashen Reach.",
      attributes_schema: {},
      obtainable: false,
      attributes: {},
    },
    {
      entity_id: "char_valerie",
      entity_type: "character",
      canonical_name: "Captain Valerie Vane",
      aliases: [],
      description: "Vanguard Commander · Iron Legion",
      attributes_schema: {
        standing: { type: "number", label: "Standing" },
        role: { type: "string", label: "Tactical Role" },
        mood: { type: "string", label: "Current Mood" },
        inventory: { type: "string", label: "Inventory / Artifact" },
        quest: { type: "string", label: "Quest Link" },
        intel: { type: "string", label: "Frontier Intel" },
      },
      obtainable: false,
      attributes: {
        standing: 64,
        role: "Heavy Bulwark & Vanguard",
        mood: "Guarded over spiced stout",
        inventory: "Sunken Legion Seal & Runic Broadsword",
        quest: '"The Shattered Seal - Chapter III"',
        intel: "Valerie commands the only contingent capable of securing the low river ford if Oakhaven falls.",
      },
    },
    {
      entity_id: "char_sylas",
      entity_type: "character",
      canonical_name: "Sylas of the Ashwood",
      aliases: [],
      description: "Frontier Scholar · Ashwood Cartographers",
      attributes_schema: {
        standing: { type: "number", label: "Standing" },
        inventory: { type: "string", label: "Inventory / Artifact" },
      },
      obtainable: false,
      attributes: {
        standing: 78,
        inventory: "Carrying Oakhaven Star Cylinder",
      },
    },
    {
      entity_id: "char_marta",
      entity_type: "character",
      canonical_name: "Marta the Barkeep",
      aliases: [],
      description: "Proprietress · Hearth & Anchor",
      attributes_schema: {},
      obtainable: false,
      attributes: {},
    },
  ],
  state: {
    current_location_id: "loc_hearth_anchor",
    player: {
      coins: 142,
      energy: 85,
      inventory: ["item_compass", "item_blade"],
    },
    quests: {
      retrieval: { stage: "body_recovered" },
    },
    entities: {
      char_valerie: {
        standing: 64,
        role: "Heavy Bulwark & Vanguard",
        mood: "Guarded over spiced stout",
        inventory: "Sunken Legion Seal & Runic Broadsword",
        quest: '"The Shattered Seal - Chapter III"',
        intel: "Valerie commands the only contingent capable of securing the low river ford if Oakhaven falls.",
      },
      char_sylas: {
        standing: 78,
        inventory: "Carrying Oakhaven Star Cylinder",
      },
    },
  },
  pending_minigame: null,
  pending_check: null,
  pending_rule_check: null,
  server_time_ms: Date.now(),
  hud_hints: { meters: [] },
  rule_sheet: [],
  ended_outcome_tag: null,
  ended_outcome_title: null,
  ended_outcome_text: null,
  turns: [
    {
      id: "turn-17",
      turn_number: 17,
      action_mode: "do",
      action_text:
        "Approach the scarred mercenary captain and inquire about the wyrmling sighting near Blackwood ridge.",
      narration_text:
        "Valerie pushed her wooden flagon aside, the iron studs on her bracers clinking against the grease-stained pine. Her scarred brow furrowed as she looked you up and down, sizing up the hilt of your consecrated blade before nodding toward the empty bench.",
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: "turn-18",
      turn_number: 18,
      action_mode: "do",
      action_text:
        "Slide onto the bench opposite Sylas and place the brass compass gently on the map parchment.",
      narration_text:
        'The stone hearth of the Hearth & Anchor roars in cadence with the gusting mountain sleet outside, casting flickering amber waves across rows of weathered oak trestles. The scent of roasted venison, pine resin, and damp wool hangs thick in the rafters. At the long table beneath the guild banners, scarred vanguards and sellswords muttering over dregs of dark ale pause their dice game, their gazes lingering momentarily on the sigil etched into your mantle.\n\nBefore Captain Valerie can finish her warning regarding the Blackwood ravines, the heavy timber door yields with a dull groan. A figure cloaked in rain-soaked mantle steps over the threshold, pulling back a hood of coarse silver weave. It is Sylas—an elven cartographer whose ledger has carried bounties across three frontier baronies. He does not approach the bar; instead, he catches Valerie’s measured nod and moves with quiet haste toward your corner.\n\n"The crest of the high court still holds weight in these borderlands," Sylas whispers, unbuckling a worn brass cylinder bound with cracked wax. "Keep your voice below the clatter of the mugs. The Oakhaven wardens were not overrun by wyrmlings. The stones themselves were shattered from the inside."\n\nWith slender, soot-stained fingers, the cartographer unrolls an intricate star chart across the tallow-slick wood. The parchment is dense with geometric silver filigree, constellations that do not match the current equinox, and a broken runic seal bearing the mark of the Ashen Spire. Valerie leans closer, resting her palm on the pommel of her broadsword. She looks to you for the command.',
      image_url:
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80",
      created_at: new Date().toISOString(),
    },
  ],
};

export function FantasyPreviewPage() {
  const setPlaythrough = usePlayStore((s) => s.setPlaythrough);

  useEffect(() => {
    setPlaythrough(PREVIEW_PLAYTHROUGH);
  }, [setPlaythrough]);

  return <FantasyPlayScreen />;
}
