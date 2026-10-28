import React from "react";
import {
  BENCHMARK_LABELS,
  PEER_SCOPE_COPY,
  STATS_SECTIONS,
} from "../../constants/stats";
import { formatBenchmarkValue } from "../../lib/statsFormat";
import { StatsSection } from "./StatsSection";
import type { BenchmarksPanelProps } from "./panels.types";

export const BenchmarksPanel: React.FC<BenchmarksPanelProps> = ({ benchmarks }) => (
  <StatsSection section={STATS_SECTIONS.benchmarks}>
    <p className="font-sans text-sm text-content-muted">
      {`You vs ${PEER_SCOPE_COPY[benchmarks.peer_scope]} (median of ${benchmarks.peer_count})`}
    </p>
    <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {benchmarks.metrics.map((metric) => (
        <div
          key={metric.key}
          className="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-raised p-4"
        >
          <dt className="font-sans text-sm text-content-muted">
            {BENCHMARK_LABELS[metric.key]}
          </dt>
          <dd className="font-mono text-2xl tabular-nums text-content">
            {formatBenchmarkValue(metric.key, metric.value)}
          </dd>
          <dd className="font-mono text-xs tabular-nums text-content-muted">
            Median {formatBenchmarkValue(metric.key, metric.peer_median)}
          </dd>
        </div>
      ))}
    </dl>
  </StatsSection>
);
