import React from "react";
import { IconAlertTriangle, IconX } from "@tabler/icons-react";
import type { StrategyNoticeBannerProps } from "./StrategyOrders.types";

export const StrategyNoticeBanner: React.FC<StrategyNoticeBannerProps> = ({
  message,
  onDismiss,
}) => (
  <div
    role="alert"
    className="fixed bottom-20 left-1/2 -translate-x-1/2 z-40 pointer-events-auto flex items-center gap-2 px-3 py-2 rounded-xl bg-[#F7F0DC]/95 border border-[#A8483E]/40 shadow-lg text-xs text-[#221A12]"
  >
    <IconAlertTriangle size={14} stroke={1.75} className="text-[#A8483E] shrink-0" />
    <span>{message}</span>
    {onDismiss ? (
      <button
        type="button"
        aria-label="Dismiss notice"
        onClick={onDismiss}
        className="text-[#72787C] hover:text-[#221A12] cursor-pointer flex items-center"
      >
        <IconX size={12} stroke={2} />
      </button>
    ) : null}
  </div>
);
