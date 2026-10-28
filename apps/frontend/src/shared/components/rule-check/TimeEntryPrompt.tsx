import React, { useEffect, useRef, useState } from "react";
import { parseClockText } from "@/shared/lib/parseClockText";
import { RuleCheckCountdown } from "./RuleCheckCountdown";
import { TimeEntryPromptProps } from "./TimeEntryPrompt.types";
import { dialogClassOf, wrapperClassOf } from "./ruleCheckShell";

const MAX_ENTRY_LENGTH = 16;
const FOCUSABLE_SELECTOR = "input, button";
const BUTTON_CLASS =
  "border border-border-subtle px-4 py-2 text-left text-sm font-medium text-content transition-colors hover:bg-surface-inset disabled:cursor-not-allowed disabled:opacity-50";

interface FactRow {
  caption: string;
  value: string | null;
}

export const TimeEntryPrompt: React.FC<TimeEntryPromptProps> = ({
  prompt,
  toldLabel,
  wallLabel,
  enterLabel,
  rejectLabel,
  remainingMs,
  windowMs,
  isSubmitting,
  isUntimed = false,
  isDocked = false,
  isLocked = false,
  onEnter,
  onReject,
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [entryText, setEntryText] = useState("");
  const isEntryValid = parseClockText(entryText).length > 0;
  const isDisabled = isSubmitting || isLocked;
  const canEnter = isEntryValid && !isDisabled;
  const facts: FactRow[] = [
    { caption: "The visitor says", value: toldLabel },
    { caption: "The wall clock reads", value: wallLabel },
  ];

  useEffect(() => {
    if (isLocked) return;
    inputRef.current?.focus();
  }, [isLocked]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>): void => {
    if (event.key !== "Tab") return;
    const items = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR) ?? [],
    ).filter((item) => !item.hasAttribute("disabled"));
    const first = items[0];
    const last = items[items.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setEntryText(event.target.value);
  };

  const handleEnter = (): void => {
    if (canEnter) onEnter(entryText);
  };

  const handleInputKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement>,
  ): void => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    handleEnter();
  };

  return (
    <div className={wrapperClassOf(isDocked)}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal={!isDocked}
        aria-label="Visitor log"
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
        <dl className="space-y-2">
          {facts
            .filter((fact) => fact.value)
            .map((fact) => (
              <div key={fact.caption} className="flex justify-between gap-4">
                <dt className="text-xs text-content-faint">{fact.caption}</dt>
                <dd className="text-sm font-medium">{fact.value}</dd>
              </div>
            ))}
        </dl>
        <label className="block space-y-1">
          <span className="text-xs text-content-faint">Time for the Log</span>
          <input
            ref={inputRef}
            type="text"
            inputMode="text"
            autoComplete="off"
            maxLength={MAX_ENTRY_LENGTH}
            value={entryText}
            disabled={isDisabled}
            onChange={handleChange}
            onKeyDown={handleInputKeyDown}
            className="h-10 w-full border border-border-strong bg-surface-inset px-3 text-sm text-content focus:border-primary focus:outline-hidden focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </label>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            disabled={!canEnter}
            onClick={handleEnter}
            className={BUTTON_CLASS}
          >
            {enterLabel}
          </button>
          <button
            type="button"
            disabled={isDisabled}
            onClick={onReject}
            className={BUTTON_CLASS}
          >
            {rejectLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
