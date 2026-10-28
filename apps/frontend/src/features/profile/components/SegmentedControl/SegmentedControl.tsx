import React, { useRef } from "react";
import { getNextTabIndex } from "../../lib/profileTabs";
import type { SegmentedControlProps } from "./SegmentedControl.types";

const ITEM_BASE_CLASSES =
  "min-h-8 rounded-sm px-3 text-xs font-medium transition duration-instant motion-reduce:transition-none focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent";
const ITEM_SELECTED_CLASSES = "bg-surface-overlay text-content";
const ITEM_IDLE_CLASSES = "text-content-muted hover:text-content";
const KEY_ALIASES: Record<string, string> = {
  ArrowDown: "ArrowRight",
  ArrowUp: "ArrowLeft",
};

export const SegmentedControl = <T extends string>({
  ariaLabel,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) => {
  const itemRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const selectedIndex = options.findIndex((option) => option.value === value);

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLButtonElement>,
    currentIndex: number,
  ) => {
    const key = KEY_ALIASES[event.key] ?? event.key;
    const nextIndex = getNextTabIndex(currentIndex, options.length, key);
    if (nextIndex === null) return;
    event.preventDefault();
    const nextOption = options[nextIndex];
    onChange(nextOption.value);
    itemRefs.current[nextOption.value]?.focus();
  };

  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-inset p-1"
    >
      {options.map((option, index) => {
        const isSelected = option.value === value;
        const isTabStop = isSelected || (selectedIndex === -1 && index === 0);
        return (
          <button
            key={option.value}
            ref={(node) => {
              itemRefs.current[option.value] = node;
            }}
            type="button"
            role="radio"
            aria-checked={isSelected}
            tabIndex={isTabStop ? 0 : -1}
            onClick={() => onChange(option.value)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={`${ITEM_BASE_CLASSES} ${isSelected ? ITEM_SELECTED_CLASSES : ITEM_IDLE_CLASSES}`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
};
