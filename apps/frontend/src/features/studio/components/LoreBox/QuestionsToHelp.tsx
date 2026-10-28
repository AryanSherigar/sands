import React, { useState } from "react";
import { IconChevronRight } from "@tabler/icons-react";
import { cn } from "@/shared/lib/cn";
import { countAnsweredQuestions } from "../../lib/loreDocument";
import type { QuestionGroup } from "../../types/guide.types";
import type { QuestionsToHelpProps } from "./LoreBox.types";
import { QuestionGroupSection } from "./QuestionGroupSection";

const getQuestionIds = (groups: QuestionGroup[]): string[] =>
  groups.flatMap((group) => group.questions.map((question) => question.id));

export const QuestionsToHelp: React.FC<QuestionsToHelpProps> = ({
  groups,
  document,
  pickOptions,
  onAnswer,
  onPick,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [openGroupId, setOpenGroupId] = useState<string | null>(null);
  const questionIds = getQuestionIds(groups);
  const answeredCount = countAnsweredQuestions(document, questionIds);

  const handleToggle = (): void => setIsOpen((current) => !current);
  const handleGroupToggle = (groupId: string) => (): void =>
    setOpenGroupId((current) => (current === groupId ? null : groupId));

  return (
    <div className="rounded-md border border-border-subtle bg-surface-raised">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={handleToggle}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-meta text-content-muted hover:text-content"
      >
        <IconChevronRight
          size={14}
          aria-hidden="true"
          className={cn("transition-transform", isOpen && "rotate-90")}
        />
        <span className="font-medium">Questions to Help</span>
        <span className="ml-auto text-micro text-content-faint">
          {answeredCount} of {questionIds.length} answered
        </span>
      </button>
      {isOpen && (
        <ul className="space-y-1 border-t border-border-subtle p-2">
          {groups.map((group) => (
            <QuestionGroupSection
              key={group.id}
              group={group}
              isOpen={openGroupId === group.id}
              onToggle={handleGroupToggle(group.id)}
              document={document}
              pickOptions={pickOptions}
              onAnswer={onAnswer}
              onPick={onPick}
            />
          ))}
        </ul>
      )}
    </div>
  );
};
