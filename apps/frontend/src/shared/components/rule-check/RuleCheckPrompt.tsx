import React, { useEffect, useRef } from "react";
import { RuleCheckCountdown } from "./RuleCheckCountdown";
import { RuleCheckPromptProps } from "./RuleCheckPrompt.types";
import { dialogClassOf, wrapperClassOf } from "./ruleCheckShell";

export const RuleCheckPrompt: React.FC<RuleCheckPromptProps> = ({
  prompt,
  options,
  remainingMs,
  windowMs,
  isSubmitting,
  isUntimed = false,
  isRecall = false,
  isDocked = false,
  isLocked = false,
  onChoose,
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isLocked) return;
    dialogRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }, [isLocked]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>): void => {
    if (event.key !== "Tab") return;
    const buttons = Array.from(
      dialogRef.current?.querySelectorAll<HTMLButtonElement>("button") ?? [],
    );
    const first = buttons[0];
    const last = buttons[buttons.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const handleChoose = (optionId: string) => (): void => {
    onChoose(optionId);
  };

  return (
    <div className={wrapperClassOf(isDocked)}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal={!isDocked}
        aria-label="Timed prompt"
        onKeyDown={handleKeyDown}
        className={`${dialogClassOf(isDocked)} space-y-5 border border-border-subtle bg-surface p-6 text-content`}
      >
        <p className="text-base">{prompt}</p>
        <RuleCheckCountdown
          remainingMs={remainingMs}
          windowMs={windowMs}
          isUntimed={isUntimed}
          isLocked={isLocked}
        />
        <div
          role={isRecall ? "radiogroup" : undefined}
          aria-label={isRecall ? "Choose the original wording" : undefined}
          className="flex flex-col gap-2"
        >
          {options.map((option) => (
            <button
              key={option.id}
              type="button"
              role={isRecall ? "radio" : undefined}
              aria-checked={isRecall ? false : undefined}
              disabled={isSubmitting || isLocked}
              onClick={handleChoose(option.id)}
              className={`border border-border-subtle px-4 py-2 text-left text-sm font-medium text-content transition-colors hover:bg-surface-inset disabled:cursor-not-allowed disabled:opacity-50 ${
                isRecall ? "italic" : ""
              }`}
            >
              {isRecall ? `\u201c${option.label}\u201d` : option.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
