import React from "react";
import { IconMapPin } from "@tabler/icons-react";
import type { StrategySituationBannerProps } from "./StrategySituationBanner.types";

export const StrategySituationBanner: React.FC<StrategySituationBannerProps> = ({
  situation,
  onCenterMap,
  onReviewEvent,
  onDismiss,
}) => {
  return (
    <div
      role="alert"
      aria-live="polite"
      className="absolute top-16 left-6 z-20 max-w-md bg-parchment-panel/95 backdrop-blur-md p-4 rounded-lg shadow-lg border border-on-surface/15 animate-fade-in flex flex-col gap-2"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className="relative flex h-2.5 w-2.5 shrink-0"
            aria-label="Escalation active"
          >
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-tertiary opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-tertiary" />
          </span>
          <h3 className="font-serif-garamond text-base sm:text-lg font-bold text-tertiary leading-tight">
            {situation.title}
          </h3>
        </div>
        <button
          type="button"
          aria-label="Dismiss banner"
          title="Dismiss banner"
          onClick={onDismiss}
          className="text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer p-0.5 rounded hover:bg-on-surface/10 leading-none shrink-0"
        >
          <span aria-hidden="true" className="text-sm font-semibold">✕</span>
        </button>
      </div>

      {/* Body */}
      {situation.causeQuote && (
        <p className="font-sans-manrope text-xs text-on-surface-variant leading-relaxed">
          {situation.causeQuote}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-on-surface/10 mt-1">
        <div className="flex items-center gap-3">
          {situation.regionId ? (
            <button
              type="button"
              onClick={() => onCenterMap(situation.regionId as string)}
              className="font-sans-manrope text-xs font-semibold text-on-surface hover:text-primary-container-wilds flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <IconMapPin size={14} className="shrink-0" />
              <span>Center map on {situation.regionName}</span>
            </button>
          ) : null}
          {situation.eventId ? (
            <button
              type="button"
              onClick={() => onReviewEvent(situation.eventId as string)}
              className="font-sans-manrope text-xs font-semibold text-tertiary hover:underline cursor-pointer"
            >
              Review decision
            </button>
          ) : null}
        </div>
        <span className="text-[11px] px-2 py-0.5 rounded bg-tertiary-fixed text-on-tertiary-fixed-variant font-bold uppercase tracking-wider font-sans-manrope shrink-0">
          Stage {situation.severityStage}: {situation.severityLabel}
        </span>
      </div>
    </div>
  );
};
