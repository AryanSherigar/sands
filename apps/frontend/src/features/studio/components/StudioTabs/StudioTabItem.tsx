import React, { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { IconPointFilled, IconX } from "@tabler/icons-react";
import { OverflowMenu } from "@/shared/components/ui/OverflowMenu";
import { cn } from "@/shared/lib/cn";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import type { StudioTabItemProps } from "./StudioTabs.types";

export const StudioTabItem: React.FC<StudioTabItemProps> = ({
  tabId,
  label,
  isActive,
  isSplit,
  isSaving,
}) => {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: tabId,
  });
  const { focusTab, closeTab, closeOtherTabs, setSplit } = useStudioTabsStore.getState();
  const isShown = isActive || isSplit;
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleContextMenu = (event: React.MouseEvent): void => {
    event.preventDefault();
    setIsMenuOpen(true);
  };

  return (
    <div
      ref={setNodeRef}
      role="presentation"
      onContextMenu={handleContextMenu}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "group/tab flex shrink-0 items-center gap-1 rounded-md border pl-3 pr-1 text-meta",
        isShown
          ? "border-border-strong bg-surface-raised text-content"
          : "border-transparent text-content-muted hover:bg-white/6",
      )}
    >
      <button
        type="button"
        onClick={() => focusTab(tabId)}
        className="flex items-center gap-1 py-1.5 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
        {...attributes}
        {...listeners}
        role="tab"
        aria-selected={isActive}
      >
        {label}
        {isActive && isSaving && (
          <>
            <IconPointFilled size={12} aria-hidden="true" className="text-content-muted" />
            <span className="sr-only">Saving</span>
          </>
        )}
      </button>
      <OverflowMenu
        label={`Tab options for ${label}`}
        isOpen={isMenuOpen}
        onOpenChange={setIsMenuOpen}
        items={[
          { id: "split", label: "Split right", onSelect: () => setSplit(tabId) },
          { id: "close", label: "Close", onSelect: () => closeTab(tabId) },
          { id: "close-others", label: "Close others", onSelect: () => closeOtherTabs(tabId) },
        ]}
      />
      <button
        type="button"
        aria-label={`Close ${label}`}
        onClick={() => closeTab(tabId)}
        className="flex h-6 w-6 items-center justify-center rounded-sm text-content-faint hover:bg-white/6 hover:text-content"
      >
        <IconX size={14} aria-hidden="true" />
      </button>
    </div>
  );
};
