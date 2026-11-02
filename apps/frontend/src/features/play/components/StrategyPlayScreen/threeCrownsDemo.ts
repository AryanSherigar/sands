import type { MapDocument } from "@/shared/types/strategy-map.types";
import type { CampaignWorldView } from "../../types/simulation.types";

export const THREE_CROWNS_MAP: MapDocument = {
  "schema_version": 1,
  "source": "manual",
  "width": 1600,
  "height": 900,
  "image_url": "",
  "regions": [
    {
      "id": "aldgate",
      "name": "Aldgate",
      "terrain": "hills",
      "outline": "M 0 0 L 400 0 L 400 300 L 0 300 Z",
      "label_point": {
        "x": 200,
        "y": 150
      },
      "neighbor_ids": [
        "ashford",
        "gull_point"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "ashford",
      "name": "Ashford",
      "terrain": "plain",
      "outline": "M 400 0 L 800 0 L 800 300 L 400 300 Z",
      "label_point": {
        "x": 600,
        "y": 150
      },
      "neighbor_ids": [
        "aldgate",
        "brennmoor",
        "carrow_vale",
        "gull_point"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "brennmoor",
      "name": "Brennmoor",
      "terrain": "marsh",
      "outline": "M 800 0 L 1200 0 L 1200 300 L 800 300 Z",
      "label_point": {
        "x": 1000,
        "y": 150
      },
      "neighbor_ids": [
        "ashford",
        "dunwick",
        "kings_ford"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "dunwick",
      "name": "Dunwick",
      "terrain": "forest",
      "outline": "M 1200 0 L 1600 0 L 1600 300 L 1200 300 Z",
      "label_point": {
        "x": 1400,
        "y": 150
      },
      "neighbor_ids": [
        "brennmoor",
        "fenwatch",
        "kings_ford"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "gull_point",
      "name": "Gull Point",
      "terrain": "coast",
      "outline": "M 0 300 L 400 300 L 400 600 L 0 600 Z",
      "label_point": {
        "x": 200,
        "y": 450
      },
      "neighbor_ids": [
        "aldgate",
        "ashford",
        "carrow_vale"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "carrow_vale",
      "name": "Carrow Vale",
      "terrain": "hills",
      "outline": "M 400 300 L 800 300 L 800 600 L 400 600 Z",
      "label_point": {
        "x": 600,
        "y": 450
      },
      "neighbor_ids": [
        "ashford",
        "elmstead",
        "gull_point",
        "kings_ford"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "kings_ford",
      "name": "King's Ford",
      "terrain": "marsh",
      "outline": "M 800 300 L 1200 300 L 1200 600 L 800 600 Z",
      "label_point": {
        "x": 1000,
        "y": 450
      },
      "neighbor_ids": [
        "brennmoor",
        "carrow_vale",
        "dunwick",
        "fenwatch",
        "high_meadow"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "fenwatch",
      "name": "Fenwatch",
      "terrain": "mountain",
      "outline": "M 1200 300 L 1600 300 L 1600 600 L 1200 600 Z",
      "label_point": {
        "x": 1400,
        "y": 450
      },
      "neighbor_ids": [
        "dunwick",
        "high_meadow",
        "kings_ford"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "elmstead",
      "name": "Elmstead",
      "terrain": "coast",
      "outline": "M 400 600 L 800 600 L 800 900 L 400 900 Z",
      "label_point": {
        "x": 600,
        "y": 750
      },
      "neighbor_ids": [
        "carrow_vale",
        "high_meadow"
      ],
      "source_color": null,
      "source_ref": null
    },
    {
      "id": "high_meadow",
      "name": "High Meadow",
      "terrain": "plain",
      "outline": "M 800 600 L 1200 600 L 1200 900 L 800 900 Z",
      "label_point": {
        "x": 1000,
        "y": 750
      },
      "neighbor_ids": [
        "elmstead",
        "fenwatch",
        "kings_ford"
      ],
      "source_color": null,
      "source_ref": null
    }
  ],
  "roads": [
    {
      "region_a": "aldgate",
      "region_b": "ashford"
    },
    {
      "region_a": "ashford",
      "region_b": "carrow_vale"
    },
    {
      "region_a": "carrow_vale",
      "region_b": "elmstead"
    },
    {
      "region_a": "carrow_vale",
      "region_b": "kings_ford"
    },
    {
      "region_a": "kings_ford",
      "region_b": "high_meadow"
    }
  ]
};

export const THREE_CROWNS_WORLD = {
  "playthrough_id": "a8e008c2-d7b2-459c-b401-ed983124ccc8",
  "world_version": 1,
  "world_hash": "digest-carrow",
  "turn": 0,
  "wave": 0,
  "orders_remaining": 6,
  "status": "planning",
  "battles": [],
  "scene_id": null,
  "summary_availability": {
    "pending_count": 0,
    "latest_summary_id": null
  },
  "clock": {
    "turn": 0,
    "start_year": 1000,
    "start_month": 3
  },
  "my_faction": {
    "id": "house_carrow",
    "leader_id": "valdren",
    "treasury": 110,
    "manpower": 285,
    "stability": 65,
    "war_exhaustion": 0,
    "reputation": 0,
    "tax_rate": "normal",
    "loans": []
  },
  "ruler": {
    "name": "Lord Valdren",
    "epithet": null,
    "portrait_url": null,
    "trait_ids": [
      "cautious",
      "pragmatic"
    ],
    "ambition_ids": [
      "ambition_peace"
    ],
    "backstory": "",
    "stress": 0
  },
  "regions": [
    {
      "region_id": "aldgate",
      "owner_id": null,
      "terrain": "hills",
      "visibility": "fogged",
      "last_seen_turn": null,
      "garrison_estimate": null,
      "detail": null
    },
    {
      "region_id": "ashford",
      "owner_id": "house_ashford",
      "terrain": "plain",
      "visibility": "visible",
      "last_seen_turn": 0,
      "garrison_estimate": {
        "low": 50,
        "high": 70
      },
      "detail": null
    },
    {
      "region_id": "brennmoor",
      "owner_id": null,
      "terrain": "marsh",
      "visibility": "fogged",
      "last_seen_turn": null,
      "garrison_estimate": null,
      "detail": null
    },
    {
      "region_id": "carrow_vale",
      "owner_id": "house_carrow",
      "terrain": "hills",
      "visibility": "visible",
      "last_seen_turn": 0,
      "garrison_estimate": {
        "low": 50,
        "high": 70
      },
      "detail": {
        "id": "carrow_vale",
        "owner_id": "house_carrow",
        "population": 800,
        "wealth": 60,
        "manpower": 110,
        "unrest": 10,
        "garrison": 60,
        "faith_id": "old_faith",
        "improvements": [
          {
            "kind": "fort",
            "turns_remaining": 0
          }
        ],
        "governor_id": null,
        "claimant_ids": [],
        "occupation": null,
        "conversion_turns_remaining": 0
      }
    },
    {
      "region_id": "dunwick",
      "owner_id": null,
      "terrain": "forest",
      "visibility": "fogged",
      "last_seen_turn": null,
      "garrison_estimate": null,
      "detail": null
    },
    {
      "region_id": "elmstead",
      "owner_id": "house_carrow",
      "terrain": "coast",
      "visibility": "visible",
      "last_seen_turn": 0,
      "garrison_estimate": {
        "low": 50,
        "high": 70
      },
      "detail": {
        "id": "elmstead",
        "owner_id": "house_carrow",
        "population": 600,
        "wealth": 55,
        "manpower": 80,
        "unrest": 10,
        "garrison": 60,
        "faith_id": "old_faith",
        "improvements": [],
        "governor_id": null,
        "claimant_ids": [],
        "occupation": null,
        "conversion_turns_remaining": 0
      }
    },
    {
      "region_id": "fenwatch",
      "owner_id": "house_dunwick",
      "terrain": "mountain",
      "visibility": "visible",
      "last_seen_turn": 0,
      "garrison_estimate": {
        "low": 50,
        "high": 70
      },
      "detail": null
    },
    {
      "region_id": "gull_point",
      "owner_id": "house_ashford",
      "terrain": "coast",
      "visibility": "visible",
      "last_seen_turn": 0,
      "garrison_estimate": {
        "low": 40,
        "high": 60
      },
      "detail": null
    },
    {
      "region_id": "high_meadow",
      "owner_id": "house_carrow",
      "terrain": "plain",
      "visibility": "visible",
      "last_seen_turn": 0,
      "garrison_estimate": {
        "low": 40,
        "high": 60
      },
      "detail": {
        "id": "high_meadow",
        "owner_id": "house_carrow",
        "population": 700,
        "wealth": 50,
        "manpower": 95,
        "unrest": 10,
        "garrison": 50,
        "faith_id": "old_faith",
        "improvements": [],
        "governor_id": "gov_danica",
        "claimant_ids": [],
        "occupation": null,
        "conversion_turns_remaining": 0
      }
    },
    {
      "region_id": "kings_ford",
      "owner_id": null,
      "terrain": "marsh",
      "visibility": "visible",
      "last_seen_turn": 0,
      "garrison_estimate": {
        "low": 20,
        "high": 40
      },
      "detail": null
    }
  ],
  "armies": [
    {
      "army_id": "army_carrow_1",
      "owner_id": "house_carrow",
      "location_id": "carrow_vale",
      "commander_name": "Brand's Vanguard",
      "troops": {
        "infantry": 380,
        "cavalry": 120
      }
    },
    {
      "army_id": "army_carrow_2",
      "owner_id": "house_carrow",
      "location_id": "elmstead",
      "commander_name": "Coast Watch",
      "troops": {
        "infantry": 200
      }
    },
    {
      "army_id": "army_ashford_visible",
      "owner_id": "house_ashford",
      "location_id": "ashford",
      "commander_name": "Renaud's Legion",
      "troops": {
        "infantry": 450,
        "cavalry": 150
      }
    },
    {
      "army_id": "army_dunwick_hidden",
      "owner_id": "house_dunwick",
      "location_id": "dunwick",
      "commander_name": "Tormund's Iron Host",
      "troops": {
        "infantry": 320
      }
    },
    {
      "army_id": "army_ashford_hidden",
      "owner_id": "house_ashford",
      "location_id": "aldgate",
      "commander_name": "Aldgate Garrison",
      "troops": {
        "infantry": 250
      }
    }
  ],
  "rivals": [
    {
      "faction_id": "house_ashford",
      "name": "House Ashford",
      "leader_name": "Lady Mira",
      "relation": "neutral",
      "treasury_range": {
        "low": 100,
        "high": 200
      },
      "manpower_range": {
        "low": 400,
        "high": 600
      }
    },
    {
      "faction_id": "house_dunwick",
      "name": "House Dunwick",
      "leader_name": "Lord Harl",
      "relation": "war",
      "treasury_range": {
        "low": 80,
        "high": 150
      },
      "manpower_range": {
        "low": 300,
        "high": 500
      }
    }
  ],
  "pacts": [],
  "queued_orders": [],
  "pending_events": [],
  "event_memories": [],
  "pending_battles": [],
  "uprisings": [],
  "own_pressure": null,
  "rumors": [],
  "truces": [],
  "own_hostages": [],
  "open_mediations": [],
  "alliances": [],
  "pending_calls": [],
  "vassalages": [],
  "coalitions": [],
  "own_threat": {
    "band": "very_low",
    "factors": {
      "conquest": 0,
      "treaty_breaking": 0,
      "atrocity": 0,
      "balance": 4
    }
  },
  "pending_demands": [],
  "pending_scene": null,
  "ending": null
} as CampaignWorldView;
