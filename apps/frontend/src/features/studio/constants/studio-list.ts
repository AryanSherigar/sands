import type { StudioTab } from "../types/scenario.types";

export const MY_SCENARIOS_QUERY_KEY = "my-scenarios";
export const STUDIO_PAGE_SIZE = 10;
export const STUDIO_STALE_TIME_MS = 15 * 1000;
export const STUDIO_PUBLISHING_POLL_MS = 1000;
export const STUDIO_SEARCH_DEBOUNCE_MS = 300;
export const FIRST_LOAD_SKELETON_COUNT = 4;
export const NEXT_PAGE_SKELETON_COUNT = 2;
export const UNTITLED_SCENARIO_TITLE = "Untitled";
export const STUDIO_REVIEW_STEP_HASH = "#review";

export const STUDIO_TABS: { value: StudioTab; label: string }[] = [
  { value: "all", label: "All" },
  { value: "drafts", label: "Drafts" },
  { value: "published", label: "Published" },
  { value: "archived", label: "Archived" },
];

export const TAB_EMPTY_COPY: Record<Exclude<StudioTab, "all">, string> = {
  drafts: "No drafts",
  published: "Nothing published yet",
  archived: "No archived stories",
};
