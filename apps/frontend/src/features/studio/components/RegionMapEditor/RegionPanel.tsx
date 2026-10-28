import React, { useEffect, useRef } from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { MAX_NAME_CHARS, TERRAINS } from "@/shared/constants/mapTracing";
import type { Terrain } from "@/shared/types/strategy-map.types";
import type { RegionPanelProps } from "./RegionMapEditor.types";

const TERRAIN_OPTIONS = TERRAINS.map((terrain) => ({ value: terrain, label: terrain }));
const CHOOSE_OPTION = { value: "", label: "Choose…" };

export const RegionPanel: React.FC<RegionPanelProps> = ({
  regionId,
  name,
  terrain,
  isCapital,
  selectedCount,
  focusSignal,
  onNameChange,
  onTerrainChange,
  onCapitalChange,
  onBulkTerrainChange,
}) => {
  const nameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (focusSignal > 0) nameInputRef.current?.focus();
  }, [focusSignal]);

  if (!regionId) {
    return <p className="text-sm text-content-muted">Select a region to name it.</p>;
  }
  return (
    <div className="space-y-3">
      <Input
        ref={nameInputRef}
        aria-label="Region name"
        placeholder="Name this region"
        maxLength={MAX_NAME_CHARS}
        value={name}
        onChange={(event) => onNameChange(event.target.value)}
      />
      <Select
        aria-label="Terrain"
        options={[CHOOSE_OPTION, ...TERRAIN_OPTIONS]}
        value={terrain ?? ""}
        onChange={(event) => event.target.value && onTerrainChange(event.target.value as Terrain)}
      />
      <label className="flex items-center gap-2 text-sm text-content">
        <input type="checkbox" checked={isCapital} onChange={onCapitalChange} />
        Capital
      </label>
      {selectedCount > 1 && (
        <Select
          aria-label="Terrain for selected"
          options={[{ value: "", label: `Terrain for ${selectedCount} selected…` }, ...TERRAIN_OPTIONS]}
          value=""
          onChange={(event) => event.target.value && onBulkTerrainChange(event.target.value as Terrain)}
        />
      )}
    </div>
  );
};
