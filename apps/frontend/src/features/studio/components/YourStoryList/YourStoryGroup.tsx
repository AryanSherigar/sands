import React, { useState } from "react";
import { IconChevronRight, IconPlus } from "@tabler/icons-react";
import { cn } from "@/shared/lib/cn";
import type { YourStoryGroupProps } from "./YourStoryList.types";

export const YourStoryGroup: React.FC<YourStoryGroupProps> = ({
  label,
  count,
  addLabel,
  onAdd,
  children,
}) => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <section aria-label={label} className="group/section space-y-1">
      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-expanded={isOpen}
          onClick={() => setIsOpen((current) => !current)}
          className="flex flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-left text-micro font-semibold uppercase tracking-wide text-content-faint hover:text-content"
        >
          <IconChevronRight
            size={12}
            aria-hidden="true"
            className={cn("transition-transform", isOpen && "rotate-90")}
          />
          <span>{label}</span>
          <span className="ml-auto font-normal normal-case tracking-normal">{count}</span>
        </button>
        {onAdd && (
          <button
            type="button"
            aria-label={addLabel ?? `Add to ${label}`}
            onClick={onAdd}
            className="flex h-6 w-6 items-center justify-center rounded-md text-content-faint opacity-0 transition-opacity hover:bg-white/6 hover:text-content focus-visible:opacity-100 group-hover/section:opacity-100"
          >
            <IconPlus size={14} aria-hidden="true" />
          </button>
        )}
      </div>
      {isOpen && <div className="space-y-0.5">{children}</div>}
    </section>
  );
};
