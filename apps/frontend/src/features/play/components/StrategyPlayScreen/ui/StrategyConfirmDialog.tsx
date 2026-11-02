import { useRef } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey } from "@/shared/hooks/useEscapeKey";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";

export interface StrategyConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function StrategyConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: StrategyConfirmDialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, isOpen);
  useEscapeKey(isOpen, onCancel);
  if (!isOpen) return null;

  return createPortal(
    <div className="strategy-surface fixed inset-0 z-50 flex items-center justify-center bg-[#382f26]/40 p-4 backdrop-blur-xs">
      <div
        ref={panelRef}
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        className="strategy-rise w-full max-w-sm rounded-2xl border border-[#3A3128]/20 bg-[#F7F0DC] p-5 shadow-2xl"
      >
        <h2 className="mb-2 font-serif text-[20px] font-semibold text-[#7c2820]">{title}</h2>
        <p className="mb-4 text-[13px] leading-relaxed text-[#221a12]">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="cursor-pointer rounded-lg border border-[#3A3128]/20 bg-[#fff8f4] px-3.5 py-1.5 text-[12px] font-semibold text-[#221a12] hover:bg-[#fbebde]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="cursor-pointer rounded-lg bg-[#7c2820] px-3.5 py-1.5 text-[12px] font-semibold text-white shadow-sm hover:bg-[#9b3f35]"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
