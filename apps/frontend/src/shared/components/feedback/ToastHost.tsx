import React, { useEffect, useState } from "react";
import { IconX } from "@tabler/icons-react";
import { useToastStore } from "@/shared/stores/toast.store";
import { TOAST_DURATION_MS } from "@/shared/constants/toast";
import { cn } from "@/shared/lib/cn";
import type { ToastKind } from "@/shared/types/toast.types";

const KIND_CLASSES: Record<ToastKind, string> = {
  error: "border-danger/50 text-danger",
  success: "border-success/50 text-success",
  info: "border-border-strong text-content",
};

export const ToastHost: React.FC = () => {
  const current = useToastStore((state) => state.queue[0]);
  const dismissToast = useToastStore((state) => state.dismissToast);
  const [isPaused, setIsPaused] = useState(false);
  const currentId = current?.id;

  useEffect(() => {
    if (currentId === undefined || isPaused) return undefined;
    const timer = setTimeout(() => dismissToast(currentId), TOAST_DURATION_MS);
    return () => clearTimeout(timer);
  }, [currentId, isPaused, dismissToast]);

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex justify-center px-4 md:inset-x-auto md:bottom-6 md:right-6 md:justify-end"
    >
      {current && (
        <div
          role="status"
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
          onFocus={() => setIsPaused(true)}
          onBlur={() => setIsPaused(false)}
          className={cn(
            "pointer-events-auto flex max-w-sm items-center gap-3 rounded-lg border bg-surface-overlay px-4 py-3 font-sans text-sm shadow-elevated",
            KIND_CLASSES[current.kind],
          )}
        >
          <span>{current.message}</span>
          {current.action && (
            <button
              type="button"
              onClick={() => {
                current.action?.onClick();
                dismissToast(current.id);
              }}
              className="font-medium text-content underline underline-offset-2 hover:text-primary focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
            >
              {current.action.label}
            </button>
          )}
          <button
            type="button"
            aria-label="Dismiss"
            onClick={() => dismissToast(current.id)}
            className="text-content-faint hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
          >
            <IconX size={14} />
          </button>
        </div>
      )}
    </div>
  );
};
