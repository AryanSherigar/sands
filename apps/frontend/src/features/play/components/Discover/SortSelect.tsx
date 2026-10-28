import React, { useState, useRef, useEffect } from "react";
import { IconChevronDown, IconCheck } from "@tabler/icons-react";
import { SORT_OPTIONS } from "../../constants/discover.constants";
import type { DiscoverSort } from "../../types/discover.types";
import type { SortSelectProps } from "./SortSelect.types";

const ICON_SIZE = 14;

export const SortSelect: React.FC<SortSelectProps> = ({ value, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent): void => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent): void => {
      if (event.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  const selectedLabel = SORT_OPTIONS.find((opt) => opt.value === value)?.label ?? value;

  const handleToggle = (): void => setIsOpen((prev) => !prev);

  const handleSelect = (next: DiscoverSort): void => {
    onChange(next);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={handleToggle}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className="flex h-9 items-center gap-2 rounded-lg border border-border-subtle bg-surface-raised px-3 text-xs font-medium text-content transition-colors hover:bg-surface-overlay focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
      >
        <span className="text-content-faint">Sort:</span>
        <span className="font-semibold">{selectedLabel}</span>
        <IconChevronDown
          size={ICON_SIZE}
          aria-hidden="true"
          className={`text-content-muted transition-transform duration-150 ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {isOpen && (
        <ul
          role="listbox"
          aria-label="Sort order"
          className="absolute right-0 z-50 mt-1.5 w-36 overflow-hidden rounded-lg border border-border-subtle bg-surface-overlay py-1 text-sm shadow-elevated"
        >
          {SORT_OPTIONS.map((option) => {
            const isSelected = option.value === value;
            return (
              <li
                key={option.value}
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(option.value)}
                className={`flex cursor-pointer items-center justify-between px-3 py-2 transition-colors ${
                  isSelected
                    ? "text-content"
                    : "text-content-muted hover:bg-surface-raised hover:text-content"
                }`}
              >
                {option.label}
                {isSelected && (
                  <IconCheck size={ICON_SIZE} aria-hidden="true" className="text-content-muted" />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};
