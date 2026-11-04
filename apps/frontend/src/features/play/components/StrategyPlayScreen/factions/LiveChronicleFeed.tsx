import React, { useState } from "react";
import { IconArrowUpRight, IconBook2, IconRefresh } from "@tabler/icons-react";
import {
  useStrategySummaries,
  useStrategySummaryStream,
} from "../../../hooks/useStrategySummaries";
import { getChronicler } from "../../../constants/chroniclers";
import { StrategyArtSlot } from "../art/StrategyArtSlot";
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

function SummaryEntry({ playthroughId, summary, isStreaming, onOpen, onJumpToRegion, chroniclerName }: {
  playthroughId?: string;
  summary: StrategySummaryView;
  isStreaming: boolean;
  onOpen: () => void;
  onJumpToRegion: (regionId: string) => void;
  chroniclerName: string;
}) {
  const regionId = summary.region_ids[0];
  const isReady = summary.status === "completed";
  const [isIllustrationRequested, setIsIllustrationRequested] = useState(false);

  const handleIllustrate = () => setIsIllustrationRequested(true);
  return (
    <article className="rounded-md border border-border-subtle bg-surface-raised p-3">
      <div className="flex items-center justify-between gap-2 text-meta text-content-muted">
        <span>{triggerLabel[summary.trigger]}</span>
        <span>Turn {summary.requested_turn + 1}</span>
      </div>
      {isReady && isIllustrationRequested ? (
        <div className="mt-2">
          <StrategyArtSlot
            playthroughId={playthroughId}
            kind="chronicle"
            itemId={summary.summary_id}
            altText="Illustration of the chronicle"
          />
        </div>
      ) : null}
      {summary.narration ? (
        <div className="mt-2 flex flex-col gap-1.5">
          <p className="whitespace-pre-wrap text-body text-content">
            {summary.narration}
          </p>
          <span className="text-[10px] text-content-muted italic">
            Inscribed by {chroniclerName}
          </span>
        </div>
      ) : (
        <p className="mt-2 text-body text-content-muted">
          {isStreaming ? `Inscribing through ${chroniclerName}…` : `Ready to be recorded by ${chroniclerName}.`}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {!isReady ? (
          <button type="button" onClick={onOpen} disabled={isStreaming} className="min-h-8 rounded-sm border border-border-strong px-2 text-meta font-semibold text-content transition-colors hover:bg-hover-wash hover:text-content focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-40">
            {actionLabel(summary, isStreaming)}
          </button>
        ) : null}
        {isReady && !isIllustrationRequested ? (
          <button type="button" onClick={handleIllustrate} className="min-h-8 rounded-sm border border-border-strong px-2 text-meta font-semibold text-content transition-colors hover:bg-hover-wash hover:text-content focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
            Illustrate
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
  chroniclerId,
  onJumpToRegion,
}) => {
  const summaries = useStrategySummaries(playthroughId);
  const stream = useStrategySummaryStream(playthroughId);
  const activeChronicler = getChronicler(chroniclerId);

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
      <div className="flex items-center justify-between text-meta font-semibold uppercase tracking-wider text-content-muted">
        <div className="flex items-center gap-2">
          <IconBook2 size={16} stroke={1.75} aria-hidden="true" />
          <span>Chronicle</span>
        </div>
      </div>

      <div className="flex flex-col gap-1 p-2 rounded-lg bg-[#FAF0E6]/80 border border-[#3A3128]/15">
        <span className="text-xs font-bold text-[#3A3128]">
          {activeChronicler.name} ({activeChronicler.title})
        </span>
        <p className="text-[11px] text-[#554A40] italic leading-tight">
          "{activeChronicler.tagline}"
        </p>
      </div>

      {stream.error ? <p className="text-body text-danger" role="alert">{stream.error.message}</p> : null}
      {stream.streaming ? (
        <article className="rounded-md border border-border-strong bg-surface-raised p-3" aria-live="polite">
          <p className="whitespace-pre-wrap text-body text-content">
            {stream.streaming.narration || `Inscribing through ${activeChronicler.name}…`}
          </p>
        </article>
      ) : null}
      {entries.length === 0 ? (
        <div className="flex flex-col gap-1 py-4 text-body text-content-muted">
          <span className="font-semibold text-content">No chronicle entries yet</span>
          <span>Major events will appear here after they are resolved.</span>
        </div>
      ) : (
        entries.map((summary) => (
          <SummaryEntry
            key={summary.summary_id}
            playthroughId={playthroughId}
            summary={summary}
            isStreaming={stream.streaming?.summaryId === summary.summary_id}
            onOpen={() => stream.start(summary)}
            onJumpToRegion={onJumpToRegion}
            chroniclerName={activeChronicler.name}
          />
        ))
      )}
    </section>
  );
};
