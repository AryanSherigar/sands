import React, { useCallback, useEffect, useRef, useState } from "react";
import { IconDots } from "@tabler/icons-react";
import { cn } from "@/shared/lib/cn";
import type { OverflowMenuProps } from "./OverflowMenu.types";

export const OverflowMenu: React.FC<OverflowMenuProps> = ({
  label,
  items,
  icon,
  triggerText,
  isOpen: controlledIsOpen,
  onOpenChange,
}) => {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const isOpen = controlledIsOpen ?? internalIsOpen;
  const setIsOpen = useCallback(
    (next: boolean): void => {
      setInternalIsOpen(next);
      onOpenChange?.(next);
    },
    [onOpenChange],
  );
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handlePointerDown = (event: MouseEvent): void => {
      if (!containerRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, setIsOpen]);

  const handleToggle = (): void => setIsOpen(!isOpen);
  const handleSelect = (onSelect: () => void) => (): void => {
    setIsOpen(false);
    onSelect();
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={handleToggle}
        className={cn(
          "flex h-8 items-center justify-center gap-1 rounded-md text-content-muted transition hover:bg-white/6 hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary",
          triggerText ? "px-2 text-meta" : "w-8",
        )}
      >
        {icon ?? <IconDots size={16} aria-hidden="true" />}
        {triggerText}
      </button>
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-1 min-w-52 rounded-md border border-border-subtle bg-surface-overlay p-1 shadow-float"
        >
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              onClick={handleSelect(item.onSelect)}
              className={cn(
                "block w-full rounded-sm px-3 py-2 text-left text-meta hover:bg-white/6 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary",
                item.isDanger ? "text-danger" : "text-content",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
