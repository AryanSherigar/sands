import { create } from "zustand";
import { UNDO_DEPTH } from "@/shared/constants/mapTracing";
import { rasterizeOutlines } from "@/shared/lib/map-tracing/rasterizeOutlines";
import type {
  LabelMap,
  MapDocument,
  RegionMeta,
  Terrain,
} from "@/shared/types/strategy-map.types";

export type RegionTool =
  | "select"
  | "merge"
  | "split"
  | "wand"
  | "lasso"
  | "brush"
  | "delete";

interface Snapshot {
  labelMap: LabelMap;
  meta: Record<string, RegionMeta>;
  capitalRegionIds: string[];
}

interface RegionMapState {
  labelMap: LabelMap | null;
  meta: Record<string, RegionMeta>;
  capitalRegionIds: string[];
  selectedId: string | null;
  selectedIds: string[];
  tool: RegionTool;
  past: Snapshot[];
  future: Snapshot[];
  reset: () => void;
  loadFromTrace: (labelMap: LabelMap) => void;
  loadFromDocument: (document: MapDocument, capitalRegionIds?: string[]) => void;
  applyEdit: (next: LabelMap) => void;
  undo: () => void;
  redo: () => void;
  setMeta: (id: string, partial: Partial<RegionMeta>) => void;
  setBulkTerrain: (ids: string[], terrain: Terrain) => void;
  toggleCapital: (id: string) => void;
  select: (id: string | null) => void;
  setSelectedIds: (ids: string[]) => void;
  setTool: (tool: RegionTool) => void;
}

function idsOf(labelMap: LabelMap): Set<string> {
  return new Set(labelMap.entries.map((entry) => entry.id));
}

const EMPTY_META: RegionMeta = { name: "", terrain: null };

function keepKnown<T>(record: Record<string, T>, known: Set<string>): Record<string, T> {
  return Object.fromEntries(Object.entries(record).filter(([id]) => known.has(id)));
}

const INITIAL_STATE = {
  labelMap: null,
  meta: {},
  capitalRegionIds: [],
  selectedId: null,
  selectedIds: [],
  tool: "select" as RegionTool,
  past: [],
  future: [],
};

function snapshotOf(state: RegionMapState): Snapshot | null {
  if (!state.labelMap) return null;
  return { labelMap: state.labelMap, meta: state.meta, capitalRegionIds: state.capitalRegionIds };
}

function restore(snapshot: Snapshot, current: RegionMapState): Partial<RegionMapState> {
  const known = idsOf(snapshot.labelMap);
  const capitals = new Set([...snapshot.capitalRegionIds, ...current.capitalRegionIds]);
  return {
    labelMap: snapshot.labelMap,
    meta: keepKnown({ ...snapshot.meta, ...current.meta }, known),
    capitalRegionIds: [...capitals].filter((id) => known.has(id)),
    selectedId: current.selectedId && known.has(current.selectedId) ? current.selectedId : null,
    selectedIds: current.selectedIds.filter((id) => known.has(id)),
  };
}

export const useRegionMapStore = create<RegionMapState>((set, get) => ({
  ...INITIAL_STATE,

  reset: () => set(INITIAL_STATE),

  loadFromTrace: (labelMap) =>
    set({ labelMap, meta: {}, capitalRegionIds: [], selectedId: null, selectedIds: [], past: [], future: [] }),

  loadFromDocument: (document, capitalRegionIds = []) =>
    set({
      labelMap: rasterizeOutlines(document),
      meta: Object.fromEntries(
        document.regions.map((region) => [region.id, { name: region.name, terrain: region.terrain }]),
      ),
      capitalRegionIds,
      selectedId: null,
      selectedIds: [],
      past: [],
      future: [],
    }),

  applyEdit: (next) => {
    const state = get();
    const before = snapshotOf(state);
    if (!before) return;
    const known = idsOf(next);
    set({
      labelMap: next,
      past: [...state.past, before].slice(-UNDO_DEPTH),
      future: [],
      meta: keepKnown(state.meta, known),
      capitalRegionIds: state.capitalRegionIds.filter((id) => known.has(id)),
      selectedId: state.selectedId && known.has(state.selectedId) ? state.selectedId : null,
      selectedIds: state.selectedIds.filter((id) => known.has(id)),
    });
  },

  undo: () => {
    const state = get();
    const present = snapshotOf(state);
    if (!present || state.past.length === 0) return;
    const previous = state.past[state.past.length - 1];
    set({ ...restore(previous, state), past: state.past.slice(0, -1), future: [present, ...state.future] });
  },

  redo: () => {
    const state = get();
    const present = snapshotOf(state);
    if (!present || state.future.length === 0) return;
    set({ ...restore(state.future[0], state), past: [...state.past, present], future: state.future.slice(1) });
  },

  setMeta: (id, partial) =>
    set((state) => ({
      meta: { ...state.meta, [id]: { ...EMPTY_META, ...state.meta[id], ...partial } },
    })),

  setBulkTerrain: (ids, terrain) =>
    set((state) => ({
      meta: {
        ...state.meta,
        ...Object.fromEntries(ids.map((id) => [id, { ...EMPTY_META, ...state.meta[id], terrain }])),
      },
    })),

  toggleCapital: (id) =>
    set((state) => ({
      capitalRegionIds: state.capitalRegionIds.includes(id)
        ? state.capitalRegionIds.filter((existing) => existing !== id)
        : [...state.capitalRegionIds, id],
    })),

  select: (id) => set({ selectedId: id, selectedIds: id ? [id] : [] }),
  setSelectedIds: (ids) => set({ selectedIds: ids, selectedId: ids[ids.length - 1] ?? null }),
  setTool: (tool) => set({ tool }),
}));
