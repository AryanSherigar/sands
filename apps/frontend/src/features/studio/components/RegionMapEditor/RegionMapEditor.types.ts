import type {
  MapDocument,
  MapProblem,
  Terrain,
} from "@/shared/types/strategy-map.types";
import type { RegionTool } from "../../stores/regionMap.store";

export interface RegionMapEditorProps {
  pictureUrl: string;
  pictureSize: { width: number; height: number };
  initialDocument: MapDocument | null;
  onFinish: (result: RegionMapResult) => void;
}

export interface RegionMapResult {
  document: MapDocument;
  capitalRegionIds: string[];
}

export interface ProblemListProps {
  problems: MapProblem[];
  regionNameById: Record<string, string>;
  onSelectRegion: (regionId: string) => void;
}

export interface ToolPaletteProps {
  tool: RegionTool;
  canUndo: boolean;
  canRedo: boolean;
  onToolChange: (tool: RegionTool) => void;
  onUndo: () => void;
  onRedo: () => void;
  onNewRegion: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
}

export interface RegionPanelProps {
  regionId: string | null;
  name: string;
  terrain: Terrain | null;
  isCapital: boolean;
  selectedCount: number;
  focusSignal: number;
  onNameChange: (name: string) => void;
  onTerrainChange: (terrain: Terrain) => void;
  onCapitalChange: () => void;
  onBulkTerrainChange: (terrain: Terrain) => void;
}

export interface StartChooserProps {
  errorMessage: string | null;
  isBusy: boolean;
  onColorImageChosen: (file: File) => void;
  onTraceByHand: () => void;
}
