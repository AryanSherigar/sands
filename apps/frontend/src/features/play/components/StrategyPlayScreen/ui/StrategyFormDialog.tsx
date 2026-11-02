import { useRef } from "react";
import type { FormEvent, ReactNode } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey } from "@/shared/hooks/useEscapeKey";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";

export interface StrategyFormDialogProps {
  title: string;
  description?: string;
  submitLabel: string;
  isSubmitDisabled?: boolean;
  onSubmit: () => void;
  onCancel: () => void;
  children: ReactNode;
}

export function StrategyFormDialog({
  title,
  description,
  submitLabel,
  isSubmitDisabled = false,
  onSubmit,
  onCancel,
  children,
}: StrategyFormDialogProps) {
  const panelRef = useRef<HTMLFormElement>(null);
  useFocusTrap(panelRef, true);
  useEscapeKey(true, onCancel);

  const handleSubmit = (event: FormEvent): void => {
    event.preventDefault();
    if (!isSubmitDisabled) onSubmit();
  };

  return createPortal(
    <div className="strategy-surface fixed inset-0 z-50 flex items-center justify-center bg-[#382f26]/40 p-4 backdrop-blur-xs">
      <form
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onSubmit={handleSubmit}
        className="strategy-rise flex max-h-full w-full max-w-sm flex-col gap-3 overflow-y-auto rounded-2xl border border-[#3A3128]/20 bg-[#F7F0DC] p-5 shadow-2xl"
      >
        <h2 className="font-serif text-[20px] font-semibold text-[#2e4856]">{title}</h2>
        {description ? <p className="text-[12px] text-[#42474b]">{description}</p> : null}
        {children}
        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onCancel}
            className="cursor-pointer rounded-lg border border-[#3A3128]/20 bg-[#fff8f4] px-3.5 py-1.5 text-[12px] font-semibold text-[#221a12] hover:bg-[#fbebde]"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="cursor-pointer rounded-lg bg-[#2e4856] px-3.5 py-1.5 text-[12px] font-semibold text-white hover:bg-[#46606E] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitLabel}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}
