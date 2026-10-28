import type {
  ScenarioMode,
  ScenarioSortField,
} from "@/shared/types/scenarioSummary.types";
import type {
  DiscoverFilters,
  DiscoverLibrary,
  DiscoverSort,
  DiscoverType,
  DiscoverView,
} from "../types/discover.types";

export const DISCOVER_PAGE_SIZE = 10;
export const DISCOVER_STALE_TIME_MS = 30 * 1000;
export const DISCOVER_VIEW_STORAGE_KEY = "discover-view";
export const DEFAULT_DISCOVER_VIEW: DiscoverView = "list";
export const ROW_SKELETON_COUNT = 6;
export const NEXT_PAGE_SKELETON_COUNT = 3;
export const POSTER_SKELETON_COUNT = 10;

export const DEFAULT_DISCOVER_FILTERS: DiscoverFilters = {
  query: "",
  genres: [],
  type: null,
  library: null,
  sort: "popular",
  isMatureIncluded: false,
};

export const SORT_OPTIONS: { value: DiscoverSort; label: string }[] = [
  { value: "top", label: "Top rated" },
  { value: "popular", label: "Popular" },
  { value: "new", label: "New" },
];

export const SORT_TO_API_FIELD: Record<DiscoverSort, ScenarioSortField> = {
  top: "rating_avg",
  popular: "play_count",
  new: "created_at",
};

export const LEGACY_SORT_ALIASES: Record<string, DiscoverSort> = {
  trending: "top",
  created_at: "new",
};

export const TYPE_OPTIONS: { value: DiscoverType; label: string }[] = [
  { value: "simple", label: "Simple" },
  { value: "advanced", label: "Advanced" },
];

export const TYPE_TO_API_MODE: Record<DiscoverType, ScenarioMode> = {
  simple: "newbie",
  advanced: "master",
};

export const LIBRARY_OPTIONS: { value: DiscoverLibrary; label: string }[] = [
  { value: "played", label: "Played" },
  { value: "saved", label: "Saved" },
  { value: "created", label: "Created" },
];

export const LIBRARY_URL_PARAMS: Record<DiscoverLibrary, string> = {
  played: "played",
  saved: "saved",
  created: "mine",
};

export const VIEW_OPTIONS: { value: DiscoverView; label: string }[] = [
  { value: "list", label: "List" },
  { value: "grid", label: "Grid" },
];

export const URL_PARAM = {
  query: "q",
  genre: "genre",
  type: "type",
  sort: "sort",
  mature: "mature",
} as const;

export const TRUE_PARAM_VALUE = "true";
export const FALSE_PARAM_VALUE = "false";

export const DEFAULT_GENRE_DOT_CLASS = "bg-[#6B7280]";

export const GENRE_DOT_CLASSES: Record<string, string> = {
  "High Fantasy": "bg-[#D4AF6A]",
  "Sci-Fi": "bg-[#4FD1E8]",
  "Adventure/Survival": "bg-[#7FA65C]",
  "Slice of Life": "bg-[#C98BA8]",
  "Noir / Detective": "bg-[#C97A3D]",
  "Post-Apocalyptic/Dystopian": "bg-[#9B9B7A]",
  Cyberpunk: "bg-[#E23FA8]",
  Horror: "bg-[#8B2635]",
  "Historical Fiction": "bg-[#A98467]",
  Mystery: "bg-[#5B6EE1]",
};
