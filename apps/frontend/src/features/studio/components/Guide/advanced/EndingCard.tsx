import React, { useMemo, useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { IconGripVertical, IconLock } from "@tabler/icons-react";
import { Input } from "@/shared/components/ui/Input";
import type { OverflowMenuItem } from "@/shared/components/ui/OverflowMenu.types";
import {
  DELETE_LABEL,
  DUPLICATE_LABEL,
  MISSING_VALUE_BLOCK_MESSAGE,
  MOVE_DOWN_LABEL,
  MOVE_UP_LABEL,
  TEST_ENDING_LABEL,
} from "../../../constants/advancedCards";
import { ENDING_QUESTION_GROUPS } from "../../../constants/advancedQuestions";
import { useValueOptions } from "../../../hooks/useValueOptions";
import { useOpenFullEditor } from "../../../hooks/useOpenFullEditor";
import { useRowAutosave } from "../../../hooks/useRowAutosave";
import { useTestSentence } from "../../../hooks/useTestSentence";
import { buildEndingDraft, buildEndingPatch, type EndingDraft } from "../../../lib/endingDraft";
import { loreToText, textToLore } from "../../../lib/loreText";
import { parseExpression } from "../../../lib/sentenceCompiler";
import type { OutcomeTag } from "../../../types/end_condition.types";
import type { LoreDocument } from "../../../types/lore.types";
import { LoreBox } from "../../LoreBox/LoreBox";
import { SentenceBuilder } from "../../SentenceBuilder/SentenceBuilder";
import type { EndingCardProps } from "./Advanced.types";
import { AdvancedCard } from "./AdvancedCard";
import { ComparisonFitNote } from "./ComparisonFitNote";
import { FieldBlock } from "./FieldBlock";

const OUTCOME_OPTIONS: Array<{ value: OutcomeTag; label: string }> = [
  { value: "win", label: "Win" },
  { value: "lose", label: "Lose" },
];
const SECRET_HELP = "Hidden from your story page until a player finds it";

const buildMenuItems = (props: EndingCardProps, onTest: () => void): OverflowMenuItem[] => {
  const items: OverflowMenuItem[] = [];
  if (props.index > 0) items.push({ id: "up", label: MOVE_UP_LABEL, onSelect: () => props.onMove(-1) });
  if (props.index < props.count - 1) {
    items.push({ id: "down", label: MOVE_DOWN_LABEL, onSelect: () => props.onMove(1) });
  }
  items.push({ id: "duplicate", label: DUPLICATE_LABEL, onSelect: props.onDuplicate });
  items.push({ id: "test", label: TEST_ENDING_LABEL, onSelect: onTest });
  items.push({ id: "delete", label: DELETE_LABEL, isDanger: true, onSelect: props.onDelete });
  return items;
};

export const EndingCard: React.FC<EndingCardProps> = (props) => {
  const { ending, index, onUpdate } = props;
  const options = useValueOptions();
  const openFullEditor = useOpenFullEditor();
  const testSentence = useTestSentence();
  const [isValid, setIsValid] = useState(true);
  const [rich, setRich] = useState<LoreDocument | null>(null);
  const sortable = useSortable({ id: ending.end_condition_id });
  const serverDraft = useMemo(() => buildEndingDraft(ending), [ending]);
  const { value: draft, commit, flush } = useRowAutosave<EndingDraft>({
    serverDraft,
    save: (next) => {
      const patch = buildEndingPatch(ending, next, !isValid);
      if (Object.keys(patch).length > 0) onUpdate(patch);
    },
  });
  const lore = rich && loreToText(rich) === draft.text ? rich : textToLore(draft.text);
  const label = `Ending ${index + 1}`;

  const handleTest = (): void => {
    flush();
    testSentence({
      kind: "ending",
      sentence: draft.expression ? parseExpression(draft.expression, draft.metadata) : null,
    });
  };
  const handleLoreChange = (next: LoreDocument): void => {
    setRich(next);
    commit({ ...draft, text: loreToText(next) });
  };

  return (
    <AdvancedCard
      ariaLabel={label}
      badge={label}
      menuLabel={`${label} options`}
      menuItems={buildMenuItems(props, handleTest)}
      cardRef={sortable.setNodeRef}
      style={{ transform: CSS.Transform.toString(sortable.transform), transition: sortable.transition }}
      leading={
        <button
          type="button"
          aria-label={`Drag to reorder ${label.toLowerCase()}`}
          className="cursor-grab text-content-faint hover:text-content-muted focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
          {...sortable.attributes}
          {...sortable.listeners}
        >
          <IconGripVertical size={16} aria-hidden="true" />
        </button>
      }
    >
      <label className="block space-y-1 text-meta font-medium text-content-muted">
        Title
        <Input
          value={draft.title}
          placeholder="Name this ending"
          onChange={(event) => commit({ ...draft, title: event.target.value })}
        />
      </label>
      <div className="flex flex-wrap items-start gap-6">
        <fieldset className="space-y-1.5">
          <legend className="text-meta font-medium text-content-muted">Result</legend>
          <div className="flex gap-4">
            {OUTCOME_OPTIONS.map((option) => (
              <label key={option.value} className="flex items-center gap-2 text-body text-content">
                <input
                  type="radio"
                  name={`${ending.end_condition_id}-result`}
                  checked={draft.tag === option.value}
                  onChange={() => commit({ ...draft, tag: option.value })}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="space-y-1">
          <label className="flex items-center gap-2 text-body text-content">
            <input
              type="checkbox"
              checked={draft.isSecret}
              onChange={(event) => commit({ ...draft, isSecret: event.target.checked })}
            />
            <IconLock size={14} aria-hidden="true" />
            Secret
          </label>
          <p className="text-micro text-content-faint">{SECRET_HELP}</p>
        </div>
      </div>
      <FieldBlock label="Ends when">
        <SentenceBuilder
          value={draft.expression}
          metadata={draft.metadata}
          onChange={(next) => commit({ ...draft, expression: next?.expression ?? null, metadata: next?.metadata })}
          onOpenFullEditor={openFullEditor}
          onValidityChange={setIsValid}
        />
        {!isValid && <p className="text-meta text-danger">{MISSING_VALUE_BLOCK_MESSAGE}</p>}
        <ComparisonFitNote expression={draft.expression} metadata={draft.metadata} options={options} />
      </FieldBlock>
      <FieldBlock label="What the player reads">
        <LoreBox
          document={lore}
          onChange={handleLoreChange}
          questions={ENDING_QUESTION_GROUPS}
          ariaLabel={`What the player reads (${label})`}
          placeholder="What the player reads when the story ends here."
        />
      </FieldBlock>
    </AdvancedCard>
  );
};
