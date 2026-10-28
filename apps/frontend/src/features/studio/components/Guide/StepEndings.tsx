import React from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Button } from "@/shared/components/ui/Button";
import { useEndingCommands } from "../../hooks/useEndingCommands";
import { getGuideStep } from "../../lib/guideSteps";
import { EndingCard } from "./advanced/EndingCard";
import { GuideStepLayout } from "./GuideStepLayout";

const DRAG_ACTIVATION_DISTANCE_PX = 4;
const EMPTY_COPY = "No endings yet. Add a win or a lose ending so your story can finish.";
const ORDER_HELP = "If two endings happen at once, the higher one wins.";

export const StepEndings: React.FC = () => {
  const commands = useEndingCommands();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: DRAG_ACTIVATION_DISTANCE_PX } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const { endings } = commands;

  const handleDragEnd = ({ active, over }: DragEndEvent): void => {
    if (over && active.id !== over.id) commands.dragEnding(String(active.id), String(over.id));
  };

  return (
    <GuideStepLayout step={getGuideStep("endings")}>
      {endings.length === 0 && !commands.isLoading && (
        <p className="text-meta text-content-muted">{EMPTY_COPY}</p>
      )}
      {endings.length > 1 && <p className="text-meta text-content-muted">{ORDER_HELP}</p>}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext
          items={endings.map((ending) => ending.end_condition_id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-4">
            {endings.map((ending, index) => (
              <EndingCard
                key={ending.end_condition_id}
                ending={ending}
                index={index}
                count={endings.length}
                onUpdate={(patch) => commands.updateEnding(ending.end_condition_id, patch)}
                onDuplicate={() => commands.duplicateEnding(ending)}
                onDelete={() => commands.deleteEnding(ending.end_condition_id)}
                onMove={(offset) => commands.moveEnding(ending.end_condition_id, offset)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" onClick={() => commands.addEnding("win")}>
          + Win ending
        </Button>
        <Button type="button" variant="secondary" onClick={() => commands.addEnding("lose")}>
          + Lose ending
        </Button>
      </div>
    </GuideStepLayout>
  );
};
