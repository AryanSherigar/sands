import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IconSearch } from "@tabler/icons-react";
import {
  DISCOVER_PATH,
  SEARCH_FOCUS_SHORTCUT_KEY,
  SEARCH_PLACEHOLDER,
} from "@/shared/constants/navigation";
import { cn } from "@/shared/lib/cn";
import type { SearchFieldProps } from "./SearchField.types";

const isTypingTarget = (target: EventTarget | null): boolean =>
  target instanceof HTMLElement &&
  (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));

export const SearchField: React.FC<SearchFieldProps> = ({
  className,
  shouldAutoFocus = false,
  onSubmitted,
}) => {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key !== SEARCH_FOCUS_SHORTCUT_KEY || isTypingTarget(event.target)) {
        return;
      }
      event.preventDefault();
      inputRef.current?.focus();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    const trimmed = query.trim();
    void navigate(
      trimmed ? `${DISCOVER_PATH}?q=${encodeURIComponent(trimmed)}` : DISCOVER_PATH,
    );
    onSubmitted?.();
  };

  return (
    <form
      role="search"
      onSubmit={handleSubmit}
      className={cn("relative flex items-center", className)}
    >
      <IconSearch
        size={16}
        className="pointer-events-none absolute left-3 text-content-faint"
      />
      <input
        ref={inputRef}
        type="search"
        value={query}
        autoFocus={shouldAutoFocus}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={SEARCH_PLACEHOLDER}
        aria-label="Search stories"
        className="h-10 w-full rounded-lg border border-border-strong bg-surface-inset pl-10 pr-4 font-sans text-sm text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden transition-colors"
      />
    </form>
  );
};
