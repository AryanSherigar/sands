import { useRef } from "react";
import { useEscapeKey } from "@/shared/hooks/useEscapeKey";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
export interface RetreatModalProps {
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  isWithdrawing: boolean;
  errorMessage?: string | null;
}

export function RetreatModal({
  isOpen,
  onCancel,
  onConfirm,
  isWithdrawing,
  errorMessage,
}: RetreatModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, isOpen);
  useEscapeKey(isOpen && !isWithdrawing, onCancel);
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#382f26]/40 backdrop-blur-xs">
      <div ref={panelRef} role="alertdialog" aria-modal="true" aria-label="Order a strategic withdrawal" className="strategy-rise w-full max-w-sm rounded-2xl bg-[#F7F0DC] shadow-2xl p-5 border border-[#3A3128]/20">
        <div className="flex items-center gap-2.5 text-[#7c2820] mb-2">
          <span className="material-symbols-outlined text-[24px]">flag</span>
          <h2 className="font-serif text-[20px] font-semibold">Order Strategic Withdrawal?</h2>
        </div>
        <p className="text-[13px] text-[#221a12] leading-relaxed mb-4">
          Your army will try to leave the field. A withdrawal can fail, and pursuing forces may cut down more of your men as you fall back.
        </p>
        {errorMessage ? (
          <p role="alert" className="text-[12px] text-[#A8483E] mb-3">
            {errorMessage}
          </p>
        ) : null}
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            disabled={isWithdrawing}
            onClick={onCancel}
            className="px-3.5 py-1.5 rounded-lg bg-[#fff8f4] border border-[#3A3128]/20 text-[12px] uppercase font-semibold text-[#221a12] cursor-pointer hover:bg-[#fbebde]"
          >
            Stay at Post
          </button>
          <button
            type="button"
            disabled={isWithdrawing}
            onClick={onConfirm}
            className="px-3.5 py-1.5 rounded-lg bg-[#7c2820] text-white text-[12px] uppercase font-semibold cursor-pointer hover:bg-[#9b3f35] shadow-sm disabled:opacity-50"
          >
            {isWithdrawing ? "Withdrawing…" : "Confirm Retreat"}
          </button>
        </div>
      </div>
    </div>
  );
}
