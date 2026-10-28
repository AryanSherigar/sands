import type { LandingRowConfig } from "../types/landing.types";

export const LANDING_ROW_LIMIT = 18;
export const CONTINUE_ROW_LIMIT = 10;
export const LANDING_STALE_TIME_MS = 60_000;
export const FALLBACK_COVER_IMAGE_URLS = [
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCaqmJks5pMWuWqfs1rjZMjAC_gfRkg2mNfRabJH3WuO2zAUUX0E4c3hDwM5AimoMVfTQq0ryrCZ4G066D790mswtyheJ1DDQT46pjZBFGMtWkSjgOVdqqhEf1Rrd9agr23pvocO-42OEPM96v6AIEjrd79wmlBNyJ-cO4rSrDHcq0xq5wttT-N9CBgp_oV00-dGqWNd2Y3JObPODJkXREO2l843spev_jTyY2Crln7nAIfqALw_I_EcA",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuA4C2Yt59RYSPW_NeBBF0QmZ3BO-QmGODi8ip-bkvDikFmyXjMTqtc9sYrd7Zo0nVDfh6O8roDJ_Qbh__1grrpISEaqShbi9UiBNajl9TqQLDSJFukpLGk3ezB6tOVGxKvw_vbmRRhNJIERiS0BEnFGstcp_hpkg_zHzkMCQ4TIJDV9RUd7RCEywmjRLP4BZ4J-wFxBGagQN7jAUZmQqc7vdiZlxxYeb6bIsVZEiIEC6h6e2CzO0nnsYg",
  "https://lh3.googleusercontent.com/aida/AEtjO1U0rEVlwrQiDFJg_B2U7NyBN1Tc6E9Zku32EOs6qGCvX9PMy9OMqVexdz0FdrqYMslaWIkPIHXMj3ZitI_OrloQNoQ6GT9O2Robkbi1ATtWz5ZTK1QPWV-4Y3dNzjqf6KamLonPm_W33h6AefTsR6ZoUyBQIpmYpY87kXJ8ufs-rDh34rwXVo6qRx6TnqNFR6W14CchK_i8WW73usbqjxYj_r9fa1HDDPkd5orCxqiLdyaSTvJlc8nXeaA",
] as const;

export const DISCOVER_PATH = "/discover";
export const SCENARIO_PATH_PREFIX = "/scenario";
export const SETUP_PATH_PREFIX = "/setup";
export const PLAY_PATH_PREFIX = "/play";

export const TOP_RATED_ROW: LandingRowConfig = {
  id: "top-rated",
  title: "Top rated",
  sort: "rating_avg",
  discoverSort: "trending",
};

export const MODE_LABELS = {
  newbie: "Simple",
  master: "Advanced",
  strategy: "Strategy",
} as const;

export const SKELETON_ROW_COUNT = 3;
export const SKELETON_CARD_COUNT = 5;

export const CURATED_CANON_LABEL = "Curated canon";
export const FEATURED_WORLDS_TITLE = "Featured worlds";
export const IN_PROGRESS_LABEL = "In progress";
export const CONTINUE_STORY_TITLE = "Continue your story";

export const STUDIO_SHOWCASE_LABEL = "Authoring Architecture";
export const STUDIO_SHOWCASE_TITLE = "Two ways to build worlds";
export const STUDIO_SHOWCASE_DESCRIPTION =
  "Whether crafting an atmospheric premise in minutes or coding deterministic logic systems with branching entity state, sands Studio enforces rigorous narrative consistency.";

const ARCHIVIST_RULES_CODE = [
  { line: "01", indent: "", key: "scenario:", val: '"The Last Archivist of Oakhaven"' },
  { line: "02", indent: "", key: "tracked_values:", val: "" },
  { line: "03", indent: "  ", key: "vows_broken:", val: "{ type: integer, initial: 0, max: 3 }" },
  { line: "04", indent: "  ", key: "library_decay:", val: "{ type: percentage, initial: 12% }" },
  { line: "05", indent: "", key: "invariant_rules:", val: "" },
  { line: "06", indent: "  ", key: '- when: "vows_broken >= 3"', val: "" },
  { line: "07", indent: "    ", key: "trigger_state:", val: '"COLLAPSE_OF_ARCHIVE"', isDanger: true },
  { line: "08", indent: "    ", key: "narrator_mandate:", val: '"Prohibit restorative magic."' },
];

export const SIMPLE_MODE_CODE = [
  { line: "01", indent: "", key: "title:", val: '"The Hollow Cairn"' },
  { line: "02", indent: "", key: "mode:", val: "simple" },
  { line: "03", indent: "", key: "genre_tags:", val: '["dark-fantasy", "dungeon-crawl"]' },
  { line: "04", indent: "", key: "logline:", val: '"A dying warden guards a cairn that swallows grief."' },
  { line: "05", indent: "", key: "opening_scene:", val: '"Ashfall Village smells of wet ash long after fires stopped."' },
  { line: "06", indent: "", key: "narrator_mandate:", val: '"Low-magic setting. The Warden never speaks first."' },
];

export const ADVANCED_MODE_CODE = ARCHIVIST_RULES_CODE;

export const RELATIVE_TIME_UNITS: ReadonlyArray<{
  unit: Intl.RelativeTimeFormatUnit;
  milliseconds: number;
}> = [
  { unit: "day", milliseconds: 86_400_000 },
  { unit: "hour", milliseconds: 3_600_000 },
  { unit: "minute", milliseconds: 60_000 },
];
