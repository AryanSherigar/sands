import React, { useEffect } from "react";
import {
  IconAlertTriangle,
  IconCheck,
  IconFlame,
  IconHourglass,
  IconMapPin,
  IconX,
} from "@tabler/icons-react";
import type { StrategySituationsDrawerProps } from "./StrategySituationsDrawer.types";
import type { ActiveSituation } from "../../../types/situation.types";

const STAGE_COLUMNS: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-3",
  4: "grid-cols-4",
};

function formatOrders(cost: number): string {
  return `${cost} ${cost === 1 ? "Order" : "Orders"}`;
}

export const StrategySituationsDrawer: React.FC<StrategySituationsDrawerProps> = ({
  isOpen,
  situations,
  activeSituationId,
  ordersRemaining,
  onClose,
  onCenterMap,
  onExecuteLever,
  onCancelLever,
  onReviewEvent,
}) => {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const crisisCountText = `${situations.length} Active ${
    situations.length === 1 ? "Crisis" : "Crises"
  }`;

  return (
    <aside
      aria-label="Situations Drawer"
      className="fixed top-14 right-0 bottom-0 w-[520px] max-w-full bg-parchment-panel/95 backdrop-blur-xl shadow-2xl border-l border-on-surface/15 z-30 flex flex-col overflow-hidden transition-transform duration-300"
    >
      {/* Header */}
      <header className="p-5 pb-4 bg-parchment-panel/60 border-b border-on-surface/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-lg bg-tertiary/10 text-tertiary flex items-center justify-center">
              <IconFlame size={20} stroke={2} />
            </span>
            <h1 className="font-serif-garamond text-2xl font-bold text-on-surface tracking-normal">
              Situations
            </h1>
            <span className="text-xs bg-tertiary-fixed text-on-tertiary-fixed-variant px-2.5 py-0.5 rounded-full font-bold">
              {crisisCountText}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface px-2 py-1 rounded hover:bg-black/5 transition-colors text-xs font-semibold cursor-pointer"
          >
            <span>[Esc]</span>
            <IconX size={16} />
          </button>
        </div>

        <div className="flex items-center gap-2 mt-2 text-on-surface-variant">
          <p className="text-xs italic text-on-surface">
            {`Orders left: ${ordersRemaining}. You cannot mend everything.`}
          </p>
        </div>
      </header>

      {/* Card list */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {situations.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-on-surface-variant">
            <span className="text-sm font-medium">No active crises</span>
            <span className="text-xs text-outline mt-1">
              The realm currently enjoys quiet borders.
            </span>
          </div>
        ) : (
          situations.map((situation: ActiveSituation) => {
            const isActive = activeSituationId === situation.id;

            return (
              <article
                key={situation.id}
                data-testid={`situation-card-${situation.id}`}
                className={`bg-surface-container-low rounded-lg p-4 shadow-sm flex flex-col gap-3 transition border ${
                  isActive
                    ? "border-tertiary ring-1 ring-tertiary"
                    : "border-on-surface/10"
                }`}
              >
                {/* Card Header & Countdown */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded bg-tertiary/15 text-tertiary flex items-center justify-center shrink-0">
                      <IconAlertTriangle size={18} />
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-on-surface leading-tight">
                        {situation.title}
                      </h2>
                      <span className="text-xs text-outline font-mono">
                        {situation.subheading || situation.regionName}
                      </span>
                    </div>
                  </div>

                  {situation.isActionable && situation.deadlineTurn !== null ? (
                    <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-tertiary-fixed text-on-tertiary-fixed-variant shadow-sm shrink-0">
                      <IconHourglass size={12} />
                      <span className="text-[11px] font-bold uppercase tracking-wider">
                        Answer this turn
                      </span>
                    </div>
                  ) : (
                    <div className="px-2.5 py-1 rounded bg-black/5 text-on-surface-variant shrink-0 text-[11px] font-bold uppercase tracking-wider">
                      Ongoing
                    </div>
                  )}
                </div>

                {/* 4-Stage Severity Ladder */}
                <div className="bg-black/5 p-2.5 rounded flex flex-col gap-1.5">
                  <span className="text-[10px] text-on-surface-variant uppercase tracking-wider font-semibold">
                    Severity Stage Progression
                  </span>
                  <div className={`grid gap-1.5 text-[11px] ${STAGE_COLUMNS[situation.maxStage]}`}>
                    {situation.stageLabels.map((label, index) => {
                      const stage = index + 1;
                      const isPassed = stage < situation.severityStage;
                      const isCurrent = stage === situation.severityStage;
                      if (isPassed) {
                        return (
                          <div
                            key={stage}
                            className="p-1.5 rounded bg-black/5 text-on-surface-variant flex items-center justify-between"
                          >
                            <span>{`${stage}. ${label}`}</span>
                            <IconCheck
                              size={12}
                              className="text-meadow-green shrink-0"
                              aria-label="Passed"
                            />
                          </div>
                        );
                      }
                      if (isCurrent) {
                        return (
                          <div
                            key={stage}
                            className="p-1.5 rounded bg-tertiary text-white flex items-center justify-between font-bold shadow-sm"
                          >
                            <span>{`${stage}. ${label}`}</span>
                            <IconAlertTriangle
                              size={12}
                              className="text-white shrink-0"
                              aria-label="Active"
                            />
                          </div>
                        );
                      }
                      return (
                        <div
                          key={stage}
                          className="p-1.5 rounded bg-black/5 text-outline flex items-center justify-between"
                        >
                          <span className="text-[10px]">{`${stage}. ${label}`}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Causal quote callout in italics */}
                {situation.causeQuote ? (
                  <p className="italic text-xs text-on-surface/90 bg-stone-200/50 p-2.5 rounded">
                    "{situation.causeQuote}"
                  </p>
                ) : null}

                {/* Two-column Intelligence vs. If Ignored */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-black/5 p-2 rounded flex flex-col">
                    <span className="text-[10px] text-outline uppercase tracking-wider font-semibold mb-1">
                      Intelligence
                    </span>
                    {situation.intelligence &&
                    situation.intelligence.length > 0 ? (
                      <ul className="space-y-1 text-on-surface">
                        {situation.intelligence.map((intel, idx) => (
                          <li
                            key={idx}
                            className="flex items-start gap-1.5 leading-tight"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-tertiary shrink-0 mt-1" />
                            <span>{intel}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-outline italic text-[11px]">
                        No active reports
                      </span>
                    )}
                  </div>

                  <div className="bg-black/5 p-2 rounded flex flex-col justify-between">
                    <div>
                      <span className="text-[10px] text-tertiary uppercase tracking-wider font-semibold block mb-1">
                        If Ignored
                      </span>
                      <p className="text-[11px] text-on-surface-variant leading-tight">
                        {situation.ifIgnoredWarning ??
                          "No decision is waiting on this right now."}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Intervention Levers */}
                {situation.levers && situation.levers.length > 0 ? (
                  <div className="flex flex-col gap-1.5 pt-1">
                    <span className="text-[10px] text-outline uppercase tracking-wider font-semibold">
                      Intervention Levers
                    </span>
                    <div className="flex flex-col gap-1.5">
                      {situation.levers.map((lever) => (
                        <div
                          key={lever.id}
                          className="w-full px-3 py-2 bg-stone-200/60 rounded flex flex-col gap-1"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-on-surface">
                              {lever.label}
                            </span>
                            <span className="text-[10px] text-outline uppercase tracking-wider font-mono shrink-0">
                              {formatOrders(lever.orderCost)}
                            </span>
                          </div>
                          {lever.effects.length > 0 ? (
                            <span className="text-[11px] text-on-surface-variant">
                              {lever.effects.join(" • ")}
                            </span>
                          ) : null}
                          {lever.isQueued ? (
                            <button
                              type="button"
                              onClick={() =>
                                lever.queuedCommandId && onCancelLever(lever.queuedCommandId)
                              }
                              className="self-start text-[11px] font-semibold text-meadow-green hover:underline cursor-pointer"
                            >
                              Queued — cancel
                            </button>
                          ) : (
                            <button
                              type="button"
                              disabled={!lever.isAffordable}
                              onClick={() => onExecuteLever(lever)}
                              className="self-start px-2.5 py-1 rounded bg-tertiary text-white text-[11px] font-semibold hover:bg-tertiary/90 disabled:cursor-not-allowed disabled:bg-black/10 disabled:text-outline cursor-pointer"
                            >
                              {lever.isAffordable ? "Order this" : "Can't afford"}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {situation.eventId ? (
                  <button
                    type="button"
                    onClick={() => onReviewEvent(situation.eventId as string)}
                    className="w-full py-1.5 px-3 rounded bg-tertiary/10 hover:bg-tertiary/20 text-on-surface text-xs font-medium border border-tertiary/30 transition cursor-pointer"
                  >
                    Review decision
                  </button>
                ) : null}

                {/* Center map button */}
                {situation.regionId ? (
                  <button
                    type="button"
                    onClick={() => onCenterMap(situation.regionId as string)}
                    className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-primary/10 hover:bg-primary/20 text-on-surface text-xs font-medium border border-primary/20 transition cursor-pointer mt-1"
                  >
                    <IconMapPin size={14} className="text-on-surface" />
                    <span>Center map on {situation.regionName}</span>
                  </button>
                ) : null}
              </article>
            );
          })
        )}
      </div>

      {/* Footer */}
      <footer className="p-4 bg-parchment-panel/90 flex flex-col gap-1.5 shadow-sm border-t border-on-surface/10">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-on-surface">
            Decisions commit when the turn ends.
          </span>
          <span className="text-[10px] text-outline font-mono">
            [Esc] Sovereign Map
          </span>
        </div>
      </footer>
    </aside>
  );
};
