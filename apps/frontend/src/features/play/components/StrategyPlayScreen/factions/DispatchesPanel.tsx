import React from "react";
import { IconMailOpened, IconRefresh } from "@tabler/icons-react";
import { useStrategyDispatches } from "../../../hooks/useStrategyDispatches";
import { useStrategyDispatchStream } from "../../../hooks/useStrategyDispatchStream";
import type { StrategyDispatchView } from "../../../types/simulation.types";
import { DispatchEntry } from "./DispatchEntry";
import type { DispatchesPanelProps } from "./DispatchesPanel.types";
import { formatFactionName } from "./dispatchText";

const groupByRival = (dispatches: StrategyDispatchView[]): [string, StrategyDispatchView[]][] => {
  const groups = new Map<string, StrategyDispatchView[]>();
  for (const dispatch of dispatches) {
    const group = groups.get(dispatch.about_faction_id) ?? [];
    group.push(dispatch);
    groups.set(dispatch.about_faction_id, group);
  }
  return [...groups.entries()];
};

export const DispatchesPanel: React.FC<DispatchesPanelProps> = ({ playthroughId }) => {
  const dispatches = useStrategyDispatches(playthroughId);
  const stream = useStrategyDispatchStream(playthroughId);
  const handleRetry = () => void dispatches.refetch();

  if (dispatches.isLoading) {
    return <div className="p-3 text-body text-content-muted">Loading dispatches…</div>;
  }
  if (dispatches.isError) {
    return (
      <div className="flex flex-col gap-2 p-3 text-body text-content-muted" role="alert">
        <span>Dispatches could not be loaded. Try again.</span>
        <button type="button" onClick={handleRetry} className="inline-flex w-fit items-center gap-1 text-meta font-semibold text-content underline underline-offset-4">
          <IconRefresh size={14} aria-hidden="true" /> Retry
        </button>
      </div>
    );
  }

  const entries = dispatches.data ?? [];
  if (entries.length === 0) {
    return (
      <div className="flex flex-col gap-1 p-3 py-4 text-body text-content-muted">
        <span className="font-semibold text-content">No dispatches yet</span>
        <span>Envoys will write to you when they learn something worth reporting.</span>
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-4 p-3" aria-label="Dispatches">
      <div className="flex items-center gap-2 text-meta font-semibold uppercase tracking-wider text-content-muted">
        <IconMailOpened size={16} stroke={1.75} aria-hidden="true" />
        <span>Dispatches</span>
      </div>
      {groupByRival(entries).map(([factionId, group]) => (
        <div key={factionId} className="flex flex-col gap-2">
          <h3 className="text-body font-semibold text-content">{formatFactionName(factionId)}</h3>
          {group.map((dispatch) => (
            <DispatchEntry
              key={dispatch.rumor_id}
              dispatch={dispatch}
              streamedText={
                stream.streaming?.rumorId === dispatch.rumor_id ? stream.streaming.narration : null
              }
              isStreaming={stream.streaming?.rumorId === dispatch.rumor_id}
              isDegraded={stream.degradedRumorIds.includes(dispatch.rumor_id)}
              onRead={stream.start}
            />
          ))}
        </div>
      ))}
    </section>
  );
};
