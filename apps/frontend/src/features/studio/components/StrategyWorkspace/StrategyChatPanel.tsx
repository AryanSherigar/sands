import React, { useMemo } from "react";
import { useStrategyActionApplier } from "../../hooks/useStrategyActionApplier";
import { buildStrategyChatContext } from "../../lib/strategyChatContext";
import { StudioChatDrawer } from "../Layout/StudioChatDrawer";
import type { StrategyChatPanelProps } from "./StrategyWorkspace.types";

export const StrategyChatPanel: React.FC<StrategyChatPanelProps> = ({
  scenarioId,
  title,
  fields,
  mapRegions,
  activePanel,
  edit,
  isOpen,
  onOpenChange,
}) => {
  const context = useMemo(
    () => buildStrategyChatContext({ title, fields, mapRegions, activePanel }),
    [title, fields, mapRegions, activePanel],
  );
  const knownRegionIds = useMemo(() => new Set(mapRegions.map((region) => region.id)), [mapRegions]);
  const applier = useStrategyActionApplier({
    scenarioId,
    edit,
    knownRegionIds,
  });
  return (
    <StudioChatDrawer
      scenarioId={scenarioId}
      strategy={{ context, applier }}
      isOpen={isOpen}
      onOpenChange={onOpenChange}
    />
  );
};
