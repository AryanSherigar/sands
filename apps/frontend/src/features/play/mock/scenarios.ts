import { ScenarioMock } from "../types/scenario";

export const mockScenarios: ScenarioMock[] = [
  {
    id: "1",
    title: "The Crimson Citadel",
    logline:
      "Infiltrate the bleeding tower of the blood mages before the crimson moon rises.",
    rating: 4.8,
    playerCount: 1245,
    genre: "High Fantasy",
    author: "ArchMage42",
    coverImageUrl: "/images/crimson.png",
    setupInputs: [
      {
        id: "field-1",
        key: "character_origin",
        label: "Lineage of Blood",
        type: "single_select",
        description:
          "Your ancestors pledged their blood to an ancient covenant.",
        required: true,
        options: [
          {
            id: "opt-1",
            label: "House of Sunfire (Paladin)",
            value: "sunfire",
          },
          { id: "opt-2", label: "Veil of Shadows (Rogue)", value: "shadows" },
          { id: "opt-3", label: "Coven of Arcana (Mage)", value: "arcana" },
        ],
        defaultValue: "sunfire",
      },
      {
        id: "field-2",
        key: "starting_relic",
        label: "Starting Relic",
        type: "single_select",
        description: "Choose a heirloom carried past the Citadel gates.",
        required: false,
        options: [
          { id: "rel-1", label: "Shattered Sun Amulet", value: "amulet" },
          { id: "rel-2", label: "Vial of Silver Blood", value: "vial" },
          { id: "rel-3", label: "Runic Dagger of the Fallen", value: "dagger" },
        ],
      },
      {
        id: "field-3",
        key: "secret_motive",
        label: "Secret Infiltration Motive",
        type: "textarea",
        placeholder:
          "Why do you seek the core of the Crimson Citadel? (e.g. avenge a lost sibling, retrieve a forbidden tome)",
        required: false,
        options: [],
      },
    ],
  },
  {
    id: "2",
    title: "Echoes of the Abyss",
    logline:
      "A cosmic horror mystery set on a deep-space mining station where the crew has begun to hear voices.",
    rating: 4.5,
    playerCount: 890,
    genre: "Sci-Fi",
    author: "VoidWalker",
    coverImageUrl: "/images/abyss.png",
    setupInputs: [
      {
        id: "field-space-1",
        key: "station_role",
        label: "Station Assignment",
        type: "single_select",
        description: "Your role aboard Deep-Mining Station Erebus-9.",
        required: true,
        options: [
          { id: "role-1", label: "Lead Engineer", value: "engineer" },
          { id: "role-2", label: "Security Specialist", value: "security" },
          { id: "role-3", label: "Xeno-Cartographer", value: "cartographer" },
        ],
      },
      {
        id: "field-space-2",
        key: "personal_quirk",
        label: "Psychological Anomaly",
        type: "text",
        placeholder:
          "e.g. Insomnia, auditory hallucinations, irrational fear of silence",
        required: false,
        options: [],
      },
    ],
  },
  {
    id: "3",
    title: "Sands of Aethelgard",
    logline:
      "Survive the harsh desert and uncover the lost civilization buried beneath the dunes.",
    rating: 4.9,
    playerCount: 2310,
    genre: "Adventure/Survival",
    author: "DuneMaster",
    coverImageUrl: "/images/sands.png",
  },
  {
    id: "4",
    title: "The Lost Kingdom of Vanaheim",
    logline:
      "A cozy slice-of-life journey about rebuilding a forgotten village from the ground up.",
    rating: 4.2,
    playerCount: 560,
    genre: "Slice of Life",
    author: "LoreKeeper",
    coverImageUrl: "/images/hero.png",
  },
  {
    id: "5",
    title: "Whispers of the Frost",
    logline: "Solve a chilling murder mystery in an isolated snowbound lodge.",
    rating: 4.7,
    playerCount: 1780,
    genre: "Noir / Detective",
    author: "WinterBorn",
    coverImageUrl: "/images/abyss.png",
  },
  {
    id: "6",
    title: "Blade of the Sun God",
    logline:
      "Escape the crumbling ruins of a post-apocalyptic Earth using solar-powered ancient tech.",
    rating: 4.6,
    playerCount: 940,
    genre: "Post-Apocalyptic/Dystopian",
    author: "SolarFlare",
    coverImageUrl: "/images/sands.png",
  },
  {
    id: "strategy-preview",
    title: "Three Crowns: The Frontier Wilds",
    logline: "Sovereign an untamed realm amidst autumn mists, rival claims, and ancient broken covenants.",
    rating: 4.9,
    playerCount: 3420,
    genre: "Grand Strategy",
    author: "GrandChronicler",
    coverImageUrl: "/images/crimson.png",
    mode: "strategy",
    strategy_document: {
      factions: [
        {
          id: "valenreach",
          name: "Crown of Valenreach",
          color: "#46606E",
          is_playable: true,
          leader_id: "alden",
          provinces_count: 4,
          capital_seat: "Castle Highgard",
          government: "Feudal Monarchy",
          treasury: 340,
          manpower: 14200,
          specialty: "High Manpower",
          roleTag: "Selected",
          crisis: {
            title: "Autumn Equinox Crisis",
            category: "Critical Incident",
            description: "An early frost has spoiled the grain yields across Highgard outer basin. Hostile raids along northern frontier demand immediate garrisoning."
          }
        },
        {
          id: "oakhaven",
          name: "Duchy of Oakhaven",
          color: "#5E8A5A",
          is_playable: true,
          leader_id: "sylvia",
          provinces_count: 3,
          capital_seat: "Oakhaven Spire",
          government: "Elective Duchy",
          treasury: 280,
          manpower: 9600,
          specialty: "Timber & Alliances",
          roleTag: "Diplomacy",
          crisis: {
            title: "Border Logging Feud",
            category: "Territorial Dispute",
            description: "Ancient sacred groves are being cleared by frontier settlers, threatening treaties with forest tribes."
          }
        },
        {
          id: "ironmark",
          name: "Ironmark March",
          color: "#A8483E",
          is_playable: true,
          leader_id: "vladik",
          provinces_count: 3,
          capital_seat: "Fortress Ironmark",
          government: "Military March",
          treasury: 190,
          manpower: 16800,
          specialty: "Aggressive Vanguard",
          roleTag: "Martial",
          crisis: {
            title: "Mutinous Garrison",
            category: "Military Crisis",
            description: "Unpaid mercenaries in the northern pass threaten to open the gates unless double wages are granted."
          }
        },
        {
          id: "riverlands",
          name: "Riverlands Freehold",
          color: "#D2A94A",
          is_playable: true,
          leader_id: "rowena",
          provinces_count: 4,
          capital_seat: "Riverwatch Port",
          government: "Merchant Freehold",
          treasury: 650,
          manpower: 7400,
          specialty: "Golden Trade Routes",
          roleTag: "Merchant",
          crisis: {
            title: "Pirate Blockade",
            category: "Trade Distress",
            description: "River galleys have severed trade barges between the lower delta and the capital markets."
          }
        }
      ],
      leaders: [
        {
          id: "alden",
          name: "King Alden IV",
          faction_id: "valenreach",
          epithet: "Sovereign of the Marches",
          portrait_url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBsacY1r5pJ5gGVLUhuFAS4mQ99oLQChktAGMvSurMx4VOYhLC8X03qb7vxRY2dO_2fkBtAoi9tpmFzz53n7iIvFsZQsl2iWYNnCVMdhY7KBnHfllM2bErsuc1RD7Regn4Ew1aWlFZqiiKt3ZmmkhPjWHDR7zLNMIcx6HESEoDDMY-z-IIAT0yvuDUsbzvh7jqWYjDgR1__74fe8wTjh9JBd8D2VkY-ucF7BH9Cx0WMGbP8FqhUM6Re-g",
          trait_ids: ["disciplined_steward", "covenant_keeper", "cautious_tactician"],
          ambition_ids: ["ambition_granary"],
          history: "Crowned amidst the autumn mists following the sudden passing of the Old King. Revering ancient covenants, Alden strives to balance martial warlords with the hungry yeomen."
        },
        {
          id: "sylvia",
          name: "Duchess Sylvia",
          faction_id: "oakhaven",
          epithet: "Lady of the Green Spires",
          portrait_url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBsacY1r5pJ5gGVLUhuFAS4mQ99oLQChktAGMvSurMx4VOYhLC8X03qb7vxRY2dO_2fkBtAoi9tpmFzz53n7iIvFsZQsl2iWYNnCVMdhY7KBnHfllM2bErsuc1RD7Regn4Ew1aWlFZqiiKt3ZmmkhPjWHDR7zLNMIcx6HESEoDDMY-z-IIAT0yvuDUsbzvh7jqWYjDgR1__74fe8wTjh9JBd8D2VkY-ucF7BH9Cx0WMGbP8FqhUM6Re-g",
          trait_ids: ["diplomatic", "honorable", "cautious"],
          ambition_ids: ["ambition_peace"],
          history: "Elected by consensus of the Spire elders to preserve the sacred border treaties and expand commerce."
        },
        {
          id: "vladik",
          name: "Margrave Vladik",
          faction_id: "ironmark",
          epithet: "The Unyielding Hammer",
          portrait_url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBsacY1r5pJ5gGVLUhuFAS4mQ99oLQChktAGMvSurMx4VOYhLC8X03qb7vxRY2dO_2fkBtAoi9tpmFzz53n7iIvFsZQsl2iWYNnCVMdhY7KBnHfllM2bErsuc1RD7Regn4Ew1aWlFZqiiKt3ZmmkhPjWHDR7zLNMIcx6HESEoDDMY-z-IIAT0yvuDUsbzvh7jqWYjDgR1__74fe8wTjh9JBd8D2VkY-ucF7BH9Cx0WMGbP8FqhUM6Re-g",
          trait_ids: ["wrathful", "proud", "inspiring"],
          ambition_ids: ["ambition_expand"],
          history: "Hardened by twenty winters guarding the frontier pass against eastern raiders."
        },
        {
          id: "rowena",
          name: "High Warden Rowena",
          faction_id: "riverlands",
          epithet: "Mistress of the Golden Barges",
          portrait_url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBsacY1r5pJ5gGVLUhuFAS4mQ99oLQChktAGMvSurMx4VOYhLC8X03qb7vxRY2dO_2fkBtAoi9tpmFzz53n7iIvFsZQsl2iWYNnCVMdhY7KBnHfllM2bErsuc1RD7Regn4Ew1aWlFZqiiKt3ZmmkhPjWHDR7zLNMIcx6HESEoDDMY-z-IIAT0yvuDUsbzvh7jqWYjDgR1__74fe8wTjh9JBd8D2VkY-ucF7BH9Cx0WMGbP8FqhUM6Re-g",
          trait_ids: ["pragmatic", "greedy", "diplomatic"],
          ambition_ids: ["ambition_wealth"],
          history: "Rose from tollmaster daughter to sovereign oligarch through shrewd diplomacy and trade leagues."
        }
      ],
      ambitions: [
        {
          id: "ambition_granary",
          name: "The Great Granary",
          description: "Stockpile 1,000 bushels before Winter 1044 to permanently secure peasant loyalty.",
          target: 1000,
          current: 340
        },
        {
          id: "ambition_peace",
          name: "The Grand Truce Covenant",
          description: "Unite 3 factions in mutual defensive covenant without declaring an offensive war.",
          target: 3,
          current: 1
        },
        {
          id: "ambition_expand",
          name: "Sovereign of Four Crowns",
          description: "Control at least 10 provinces across the Frontier Wilds.",
          target: 10,
          current: 4
        },
        {
          id: "ambition_wealth",
          name: "The Golden Vault",
          description: "Accumulate 2,500 gold in the royal treasury.",
          target: 2500,
          current: 650
        }
      ]
    }
  },
];
