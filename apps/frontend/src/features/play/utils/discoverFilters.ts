import type {
  GetScenariosParams,
} from "@/shared/types/scenarioSummary.types";
import {
  DEFAULT_DISCOVER_FILTERS,
  LEGACY_SORT_ALIASES,
  LIBRARY_OPTIONS,
  LIBRARY_URL_PARAMS,
  SORT_OPTIONS,
  SORT_TO_API_FIELD,
  FALSE_PARAM_VALUE,
  TRUE_PARAM_VALUE,
  TYPE_OPTIONS,
  TYPE_TO_API_MODE,
  URL_PARAM,
} from "../constants/discover.constants";
import type {
  ActiveFilterChip,
  DiscoverFilters,
  DiscoverLibrary,
  DiscoverSort,
} from "../types/discover.types";

function pickOption<T extends string>(
  options: { value: T }[],
  raw: string | null,
): T | null {
  const match = options.find((option) => option.value === raw);
  return match ? match.value : null;
}

function readSort(raw: string | null): DiscoverSort {
  const sort = pickOption(SORT_OPTIONS, raw);
  if (sort) return sort;
  return (raw && LEGACY_SORT_ALIASES[raw]) || DEFAULT_DISCOVER_FILTERS.sort;
}

function readLibrary(params: URLSearchParams): DiscoverLibrary | null {
  const active = LIBRARY_OPTIONS.find(
    (option) =>
      params.get(LIBRARY_URL_PARAMS[option.value]) === TRUE_PARAM_VALUE,
  );
  return active ? active.value : null;
}

function readMature(params: URLSearchParams, isMatureDefault: boolean): boolean {
  if (!params.has(URL_PARAM.mature)) return isMatureDefault;
  return params.get(URL_PARAM.mature) === TRUE_PARAM_VALUE;
}

export function parseDiscoverFilters(
  params: URLSearchParams,
  isMatureDefault = false,
): DiscoverFilters {
  return {
    query: params.get(URL_PARAM.query)?.trim() ?? "",
    genres: params.getAll(URL_PARAM.genre),
    type: pickOption(TYPE_OPTIONS, params.get(URL_PARAM.type)),
    library: readLibrary(params),
    sort: readSort(params.get(URL_PARAM.sort)),
    isMatureIncluded: readMature(params, isMatureDefault),
  };
}

function setIfPresent(
  params: URLSearchParams,
  key: string,
  value: string | null,
): void {
  if (value) params.set(key, value);
}

export function serializeDiscoverFilters(
  filters: DiscoverFilters,
  isMatureDefault = false,
): URLSearchParams {
  const params = new URLSearchParams();
  setIfPresent(params, URL_PARAM.query, filters.query);
  filters.genres.forEach((genre) => params.append(URL_PARAM.genre, genre));
  setIfPresent(params, URL_PARAM.type, filters.type);
  if (filters.library) {
    params.set(LIBRARY_URL_PARAMS[filters.library], TRUE_PARAM_VALUE);
  }
  if (filters.sort !== DEFAULT_DISCOVER_FILTERS.sort) {
    params.set(URL_PARAM.sort, filters.sort);
  }
  if (filters.isMatureIncluded) params.set(URL_PARAM.mature, TRUE_PARAM_VALUE);
  else if (isMatureDefault) params.set(URL_PARAM.mature, FALSE_PARAM_VALUE);
  return params;
}

export function toScenarioApiParams(
  filters: DiscoverFilters,
): GetScenariosParams {
  const params: GetScenariosParams = {
    sort: SORT_TO_API_FIELD[filters.sort],
    include_mature: filters.isMatureIncluded,
  };
  if (filters.query) params.q = filters.query;
  if (filters.genres.length > 0) params.genre_tags = filters.genres;
  if (filters.type) params.mode = TYPE_TO_API_MODE[filters.type];
  if (filters.library === "played") params.played = true;
  if (filters.library === "saved") params.saved = true;
  if (filters.library === "created") params.mine = true;
  return params;
}

function labelFor(
  options: { value: string; label: string }[],
  value: string,
): string {
  return options.find((option) => option.value === value)?.label ?? value;
}

function buildSingleValueChips(filters: DiscoverFilters): ActiveFilterChip[] {
  const entries: [string, string | null, { value: string; label: string }[]][] =
    [
      ["library", filters.library, LIBRARY_OPTIONS],
      ["type", filters.type, TYPE_OPTIONS],
    ];
  return entries
    .filter(([, value]) => value !== null)
    .map(([id, value, options]) => ({
      id,
      label: labelFor(options, value as string),
    }));
}

export function buildActiveFilterChips(
  filters: DiscoverFilters,
): ActiveFilterChip[] {
  const genreChips = filters.genres.map((genre) => ({
    id: `genre:${genre}`,
    label: genre,
  }));
  const matureChips = filters.isMatureIncluded
    ? [{ id: "mature", label: "Mature included" }]
    : [];
  return [...buildSingleValueChips(filters), ...genreChips, ...matureChips];
}

export function removeFilterByChipId(
  filters: DiscoverFilters,
  chipId: string,
): DiscoverFilters {
  if (chipId.startsWith("genre:")) {
    const genre = chipId.slice("genre:".length);
    return { ...filters, genres: filters.genres.filter((g) => g !== genre) };
  }
  if (chipId === "mature") return { ...filters, isMatureIncluded: false };
  return { ...filters, [chipId]: null };
}

export function clearAllFilters(filters: DiscoverFilters): DiscoverFilters {
  return { ...DEFAULT_DISCOVER_FILTERS, sort: filters.sort };
}
