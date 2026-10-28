import React, { useMemo } from "react";
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
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import {
  LORE_BLOCK_ID_PREFIX,
  LORE_BOX_DEFAULT_LABEL,
  LORE_BOX_DEFAULT_PLACEHOLDER,
} from "../../constants/loreBox";
import { useLoreDocument } from "../../hooks/useLoreDocument";
import { getTextareaRows } from "../../lib/loreBoxLayout";
import { countWords } from "../../lib/loreDocument";
import type { GuideQuestion, PickOption } from "../../types/guide.types";
import { LinkedBlock } from "./LinkedBlock";
import type { LoreBoxProps } from "./LoreBox.types";
import { FeatureAnchor } from "../NewFeatures/FeatureAnchor";
import { QuestionsToHelp } from "./QuestionsToHelp";

const DRAG_ACTIVATION_DISTANCE_PX = 4;
const NO_PICK_OPTIONS: PickOption[] = [];

const parseBlockIndex = (id: unknown): number =>
  Number(String(id).replace(LORE_BLOCK_ID_PREFIX, ""));

export const LoreBox: React.FC<LoreBoxProps> = ({
  document,
  onChange,
  softWordGuide,
  questions,
  ariaLabel = LORE_BOX_DEFAULT_LABEL,
  placeholder = LORE_BOX_DEFAULT_PLACEHOLDER,
  pickOptions = NO_PICK_OPTIONS,
  onPick,
  onRemovePick,
  onAddToAlwaysRemember,
}) => {
  const actions = useLoreDocument(document, onChange);
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: DRAG_ACTIVATION_DISTANCE_PX },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  const questionsById = useMemo(() => {
    const entries = (questions ?? []).flatMap((group) =>
      group.questions.map((question): [string, GuideQuestion] => [
        question.id,
        question,
      ]),
    );
    return new Map(entries);
  }, [questions]);

  const hasLeadingText = document.blocks[0]?.kind === "text";
  const leadingText = hasLeadingText ? document.blocks[0].text : "";
  const firstRowIndex = hasLeadingText ? 1 : 0;
  const lastIndex = document.blocks.length - 1;
  const rowIndexes = document.blocks
    .map((_, index) => index)
    .filter((index) => index >= firstRowIndex);

  const getPickQuestion = (index: number): GuideQuestion | undefined => {
    const question = questionsById.get(document.blocks[index].question_id ?? "");
    return question?.pick ? question : undefined;
  };
  const isPickTargetMissing = (index: number): boolean => {
    const name = document.blocks[index].text.trim().toLowerCase();
    return !pickOptions.some((option) => option.name.toLowerCase() === name);
  };

  const handleLeadingChange = (
    event: React.ChangeEvent<HTMLTextAreaElement>,
  ): void => {
    if (hasLeadingText) actions.editBlock(0, event.target.value);
    else if (event.target.value) actions.prependText(event.target.value);
  };
  const handleAnswer = (question: GuideQuestion, text: string): void =>
    actions.setAnswer(question, text);
  const handlePick = (question: GuideQuestion, option: PickOption): void => {
    actions.addAnswerBlock(question, option.name);
    onPick?.(question, option);
  };
  const handleRemove = (index: number): void => {
    const pickQuestion = getPickQuestion(index);
    if (pickQuestion) onRemovePick?.(pickQuestion, document.blocks[index].text);
    actions.removeBlock(index);
  };
  const handleMove = (index: number, offset: number): void =>
    actions.reorderBlocks(index, index + offset);
  const handleDragEnd = ({ active, over }: DragEndEvent): void => {
    if (!over || active.id === over.id) return;
    actions.reorderBlocks(parseBlockIndex(active.id), parseBlockIndex(over.id));
  };

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-border-strong bg-surface-inset p-3 focus-within:border-primary">
        <textarea
          aria-label={ariaLabel}
          placeholder={placeholder}
          value={leadingText}
          rows={getTextareaRows(leadingText)}
          onChange={handleLeadingChange}
          className="w-full resize-y bg-transparent text-base leading-relaxed text-content placeholder:text-content-faint focus:outline-hidden"
        />
        {softWordGuide && (
          <div className="mt-2 flex justify-between text-micro text-content-faint">
            <span>{softWordGuide}</span>
            <span>{countWords(document)} words</span>
          </div>
        )}
      </div>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={rowIndexes.map((index) => `${LORE_BLOCK_ID_PREFIX}${index}`)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2">
            {rowIndexes.map((index) => (
              <LinkedBlock
                key={`${LORE_BLOCK_ID_PREFIX}${index}`}
                block={document.blocks[index]}
                index={index}
                canMoveUp={index > firstRowIndex}
                canMoveDown={index < lastIndex}
                isPicked={Boolean(getPickQuestion(index))}
                isMissing={
                  Boolean(getPickQuestion(index)) && isPickTargetMissing(index)
                }
                onEdit={actions.editBlock}
                onRemove={handleRemove}
                onUnlink={actions.unlinkBlock}
                onMove={handleMove}
                onAddToAlwaysRemember={onAddToAlwaysRemember}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
      {questions && questions.length > 0 && (
        <FeatureAnchor featureId="questions-to-help">
          <QuestionsToHelp
            groups={questions}
            document={document}
            pickOptions={pickOptions}
            onAnswer={handleAnswer}
            onPick={handlePick}
          />
        </FeatureAnchor>
      )}
    </div>
  );
};
