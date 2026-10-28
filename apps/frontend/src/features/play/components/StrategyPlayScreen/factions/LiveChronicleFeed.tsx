import React from "react";
import { IconArrowUpRight, IconBook2, IconRefresh } from "@tabler/icons-react";
import {
  useStrategySummaries,
  useStrategySummaryStream,
} from "../../../hooks/useStrategySummaries";
import type { StrategySummaryView } from "../../../types/simulation.types";
import type { LiveChronicleFeedProps } from "./LiveChronicleFeed.types";

const triggerLabel: Record<StrategySummaryView["trigger"], string> = {
  major_event: "Major event",
  significance: "Realm update",
};

function actionLabel(summary: StrategySummaryView, isStreaming: boolean): string {
  if (summary.status === "completed") return "Read entry";
  if (isStreaming) return "Writing…";
  return "Write entry";
}

function SummaryEntry({ summary, isStreaming, onOpen, onJumpToRegion }: {
  summary: StrategySummaryView;
  isStreaming: boolean;
  onOpen: () => void;
  onJumpToRegion: (regionId: string) => void;
}) {
  const regionId = summary.region_ids[0];
  const isReady = summary.status === "completed";
  return (
    <article className="rounded-md border border-border-subtle bg-surface-raised p-3">
      <div className="flex items-center justify-between gap-2 text-meta text-content-muted">
        <span>{triggerLabel[summary.trigger]}</span>
        <span>Turn {summary.requested_turn + 1}</span>
      </div>
      {summary.narration ? (
        <p className="mt-2 whitespace-pre-wrap text-body text-content">
          {summary.narration}
        </p>
      ) : (
        <p className="mt-2 text-body text-content-muted">
          {isStreaming ? "Writing the chronicle…" : "A new event is ready to be written."}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {!isReady ? (
          <button type="button" onClick={onOpen} disabled={isStreaming} className="min-h-8 rounded-sm border border-border-strong px-2 text-meta font-semibold text-content transition-colors hover:bg-hover-wash hover:text-content focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-40">
            {actionLabel(summary, isStreaming)}
          </button>
        ) : null}
        {regionId ? (
          <button type="button" onClick={() => onJumpToRegion(regionId)} className="inline-flex min-h-8 items-center gap-1 rounded-sm px-2 text-meta font-semibold text-content-muted transition-colors hover:bg-hover-wash hover:text-content focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
            Map
            <IconArrowUpRight size={14} stroke={1.75} aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </article>
  );
}

export const LiveChronicleFeed: React.FC<LiveChronicleFeedProps> = ({
  playthroughId,
  onJumpToRegion,
}) => {
  const summaries = useStrategySummaries(playthroughId);
  const stream = useStrategySummaryStream(playthroughId);

  if (summaries.isLoading) {
    return <div className="p-3 text-body text-content-muted">Loading chronicle…</div>;
  }
  if (summaries.isError) {
    return (
      <div className="flex flex-col gap-2 p-3 text-body text-content-muted" role="alert">
        <span>Chronicle could not be loaded. Try again.</span>
        <button type="button" onClick={() => void summaries.refetch()} className="inline-flex w-fit items-center gap-1 text-meta font-semibold text-content underline underline-offset-4">
          <IconRefresh size={14} aria-hidden="true" /> Retry
        </button>
      </div>
    );
  }

  const entries = summaries.data?.items ?? [];
  return (
    <section className="flex flex-col gap-3 p-3" aria-label="Chronicle">
      <div className="flex items-center gap-2 text-meta font-semibold uppercase tracking-wider text-content-muted">
        <IconBook2 size={16} stroke={1.75} aria-hidden="true" />
        <span>Chronicle</span>
      </div>
      {stream.error ? <p className="text-body text-danger" role="alert">{stream.error.message}</p> : null}
      {stream.streaming ? <article className="rounded-md border border-border-strong bg-surface-raised p-3" aria-live="polite"><p className="whitespace-pre-wrap text-body text-content">{stream.streaming.narration || "Writing the chronicle…"}</p></article> : null}
      {entries.length === 0 ? <div className="flex flex-col gap-1 py-4 text-body text-content-muted"><span className="font-semibold text-content">No chronicle entries yet</span><span>Major events will appear here after they are resolved.</span></div> : entries.map((summary) => <SummaryEntry key={summary.summary_id} summary={summary} isStreaming={stream.streaming?.summaryId === summary.summary_id} onOpen={() => stream.start(summary)} onJumpToRegion={onJumpToRegion} />)}
    </section>
  );
};
