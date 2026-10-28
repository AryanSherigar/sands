import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { TOOL_LABELS } from "../../constants/regionMapEditor";
import type { ToolPaletteProps } from "./RegionMapEditor.types";

export const ToolPalette: React.FC<ToolPaletteProps> = ({
  tool,
  canUndo,
  canRedo,
  onToolChange,
  onUndo,
  onRedo,
  onNewRegion,
  onZoomIn,
  onZoomOut,
  onFit,
}) => (
  <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="Map tools">
    {TOOL_LABELS.map((entry) => (
      <Button
        key={entry.id}
        size="sm"
        variant={tool === entry.id ? "primary" : "secondary"}
        aria-pressed={tool === entry.id}
        onClick={() => onToolChange(entry.id)}
      >
        {entry.label}
      </Button>
    ))}
    <Button size="sm" variant="ghost" onClick={onNewRegion}>
      New region
    </Button>
    <Button size="sm" variant="ghost" disabled={!canUndo} onClick={onUndo}>
      Undo
    </Button>
    <Button size="sm" variant="ghost" disabled={!canRedo} onClick={onRedo}>
      Redo
    </Button>
    <Button size="sm" variant="ghost" onClick={onZoomIn}>
      Zoom in
    </Button>
    <Button size="sm" variant="ghost" onClick={onZoomOut}>
      Zoom out
    </Button>
    <Button size="sm" variant="ghost" onClick={onFit}>
      Fit
    </Button>
  </div>
);
