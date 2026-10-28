import React from "react";
import {
  DndContext,
  DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { useMediaQuery } from "@/shared/hooks/useMediaQuery";
import { MOBILE_MEDIA_QUERY } from "../../constants/studioFrame";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { useStudioStore } from "../../stores/studio.store";
import { useTabLabels } from "../../hooks/useTabLabels";
import { MobileTabSwitcher } from "./MobileTabSwitcher";
import { StudioTabItem } from "./StudioTabItem";
import { TabAddMenu } from "./TabAddMenu";

const DRAG_ACTIVATION_DISTANCE_PX = 6;

export const StudioTabs: React.FC = () => {
  const isMobile = useMediaQuery(MOBILE_MEDIA_QUERY);
  const getLabel = useTabLabels();
  const openTabIds = useStudioTabsStore((state) => state.openTabIds);
  const activeTabId = useStudioTabsStore((state) => state.activeTabId);
  const splitTabId = useStudioTabsStore((state) => state.splitTabId);
  const moveTab = useStudioTabsStore((state) => state.moveTab);
  const isSaving = useStudioStore((state) => state.isSaving);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: DRAG_ACTIVATION_DISTANCE_PX } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  if (isMobile) return <MobileTabSwitcher getLabel={getLabel} />;

  const handleDragEnd = ({ active, over }: DragEndEvent): void => {
    if (!over || active.id === over.id) return;
    moveTab(openTabIds.indexOf(String(active.id)), openTabIds.indexOf(String(over.id)));
  };

  return (
    <div className="flex items-center gap-1 overflow-x-auto border-b border-border-subtle bg-surface-sunken px-3 py-2">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={openTabIds} strategy={horizontalListSortingStrategy}>
          <div role="tablist" aria-label="Open tabs" className="flex items-center gap-1">
            {openTabIds.map((tabId) => (
              <StudioTabItem
                key={tabId}
                tabId={tabId}
                label={getLabel(tabId)}
                isActive={tabId === activeTabId}
                isSplit={tabId === splitTabId}
                isSaving={isSaving}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
      <TabAddMenu />
    </div>
  );
};
