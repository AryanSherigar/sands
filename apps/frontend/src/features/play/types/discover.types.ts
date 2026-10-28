export type DiscoverSort = "top" | "popular" | "new";
export type DiscoverType = "simple" | "advanced";
export type DiscoverLibrary = "played" | "saved" | "created";
export type DiscoverView = "list" | "grid";

export interface DiscoverFilters {
  query: string;
  genres: string[];
  type: DiscoverType | null;
  library: DiscoverLibrary | null;
  sort: DiscoverSort;
  isMatureIncluded: boolean;
}

export interface ActiveFilterChip {
  id: string;
  label: string;
}
